#!/usr/bin/env bash
# =====================================================================
# TradePilot 복구 리허설 (자동)
# 파일: restore_drill.sh
# 목적:
#   매주 일요일 04:00 자동 실행. 가장 최신 풀백업을 임시 DB로 복원하고
#   drill_validation.sql 로 검증 → 결과를 Redis publish + 로그 + 알림.
#
# 합격 기준:
#   - pg_restore 종료코드 0
#   - drill_validation.sql 의 status='FAIL' 행이 0건
#   - 핵심 테이블(users, stocks, orders) 행수가 운영 DB의 80% 이상
#
# 실패 시:
#   - tp:backup.alerts CRITICAL 알림
#   - 임시 DB 는 디버깅용으로 유지 (24시간 후 자동 정리)
#
# 의존성: restore_full.sh, drill_validation.sql, psql, jq
#
# 환경변수:
#   DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
#   BACKUP_LOCAL_DIR, REDIS_URL
#
# 사용법:
#   ./restore_drill.sh
#   ./restore_drill.sh --backup-file /path/to/specific.dump.gpg
#   ./restore_drill.sh --keep-db   (검증 후 DB 유지)
#
# Cron 예: 0 4 * * 0 /opt/tradepilot/infra/backup/restore_drill.sh
# =====================================================================

SCRIPT_NAME="restore_drill.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

BACKUP_FILE_OVERRIDE=""
KEEP_DB=false

while (( $# > 0 )); do
    case "$1" in
        --backup-file) shift; BACKUP_FILE_OVERRIDE="$1" ;;
        --keep-db) KEEP_DB=true ;;
        --dry-run) DRY_RUN=true ;;
        -h|--help)
            cat <<EOF
사용법: $0 [옵션]
  --backup-file <path>  특정 백업 파일 지정(기본: 최신 풀백업)
  --keep-db             검증 후 임시 DB 유지(디버깅)
  --dry-run             명령은 출력만
EOF
            exit 0 ;;
    esac
    shift
done

main() {
    log_setup
    load_env
    require_env DB_HOST DB_PORT DB_USER BACKUP_LOCAL_DIR
    export_pgpassword
    acquire_lock restore_drill

    local started_at
    started_at=$(date +%s)
    emit_backup_event started drill '{}'

    # ---- 백업 파일 선택 -------------------------------------------
    local backup_file="${BACKUP_FILE_OVERRIDE}"
    if [[ -z "${backup_file}" ]]; then
        # 가장 최신 .dump.gpg 또는 .dump.age 또는 .dump
        backup_file=$(find "${BACKUP_LOCAL_DIR}/full" -maxdepth 1 -type f \
            \( -name 'tradepilot_*.dump.gpg' -o -name 'tradepilot_*.dump.age' -o -name 'tradepilot_*.dump' \) \
            -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | awk '{print $2}')
    fi

    if [[ -z "${backup_file}" || ! -f "${backup_file}" ]]; then
        log_error "리허설용 백업 파일을 찾지 못함"
        emit_backup_event failure drill '{"error":"no_backup_file"}'
        emit_backup_alert CRITICAL "TradePilot 복구 리허설 실패: 백업 파일 없음"
        exit 20
    fi

    log_info "리허설 대상 백업: ${backup_file}"

    # ---- 임시 DB 이름 ---------------------------------------------
    local target_db="tradepilot_drill_$(date +%Y%m%d_%H%M)"

    # 24시간 이상 묵은 이전 drill DB 정리
    cleanup_stale_drill_dbs

    # ---- 복원 ------------------------------------------------------
    log_info "임시 DB 복원: ${target_db}"
    local restore_log="${BACKUP_LOCAL_DIR}/log/drill_restore_$(date +%Y%m%d_%H%M).log"

    if ! "${SCRIPT_DIR}/restore_full.sh" \
            --yes \
            --jobs "${PG_DUMP_JOBS:-2}" \
            "${backup_file}" "${target_db}" > "${restore_log}" 2>&1; then
        log_error "pg_restore 실패. 로그: ${restore_log}"
        emit_backup_event failure drill \
            "$(printf '{"phase":"restore","backup":"%s","log":"%s"}' \
                "$(basename "${backup_file}")" "${restore_log}")"
        emit_backup_alert CRITICAL "TradePilot 복구 리허설 실패(restore): $(basename "${backup_file}")"
        exit 21
    fi
    log_ok "복원 완료: ${target_db}"

    # ---- 검증 ------------------------------------------------------
    log_info "drill_validation.sql 실행"
    local validation_log="${BACKUP_LOCAL_DIR}/log/drill_validation_$(date +%Y%m%d_%H%M).log"

    if ! psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${target_db}" \
            -v ON_ERROR_STOP=1 \
            -f "${SCRIPT_DIR}/drill_validation.sql" > "${validation_log}" 2>&1; then
        log_error "검증 SQL 실패. 로그: ${validation_log}"
        emit_backup_event failure drill \
            "$(printf '{"phase":"validation","db":"%s","log":"%s"}' \
                "${target_db}" "${validation_log}")"
        emit_backup_alert CRITICAL "TradePilot 복구 리허설 실패(validation)"
        # DB는 디버깅용 유지
        return 22
    fi

    # FAIL 카운트 검사
    local fail_count
    fail_count=$(grep -ciE '\| *FAIL' "${validation_log}" || true)
    if (( fail_count > 0 )); then
        log_error "검증 FAIL: ${fail_count}건. 로그: ${validation_log}"
        emit_backup_event failure drill \
            "$(printf '{"phase":"validation","fail_count":%s}' "${fail_count}")"
        emit_backup_alert CRITICAL "TradePilot 복구 리허설 검증 FAIL ${fail_count}건"
        return 23
    fi

    # ---- 운영 DB 대비 행수 비율 (80% 이상) ------------------------
    log_info "운영 DB 대비 행수 비율 점검"
    local ratio_ok=true
    for tbl in "tp_user.users" "tp_market.stocks" "tp_trade.orders"; do
        local prod_cnt drill_cnt
        prod_cnt=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -At \
            -c "SELECT COUNT(*) FROM ${tbl}" 2>/dev/null || echo 0)
        drill_cnt=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${target_db}" -At \
            -c "SELECT COUNT(*) FROM ${tbl}" 2>/dev/null || echo 0)
        log_info "  ${tbl}: 운영=${prod_cnt} / 리허설=${drill_cnt}"

        # 운영이 0이면 비교 의미 없음
        if (( prod_cnt > 0 )); then
            local pct=$(( drill_cnt * 100 / prod_cnt ))
            if (( pct < 80 )); then
                log_warn "  → 행수 비율 ${pct}% < 80% (백업 시점 차이일 수 있음)"
                ratio_ok=false
            fi
        fi
    done

    # ---- 정리 ------------------------------------------------------
    if [[ "${KEEP_DB}" == "true" ]]; then
        log_warn "--keep-db: 임시 DB 유지 (${target_db})"
    else
        log_info "임시 DB DROP: ${target_db}"
        run_cmd psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
            -c "DROP DATABASE IF EXISTS \"${target_db}\";"
    fi

    local elapsed=$(( $(date +%s) - started_at ))
    local extra
    extra=$(printf '{"backup":"%s","drill_db":"%s","duration_sec":%s,"ratio_ok":%s,"validation_log":"%s"}' \
        "$(basename "${backup_file}")" "${target_db}" "${elapsed}" "${ratio_ok}" "$(basename "${validation_log}")")

    emit_backup_event success drill "${extra}"
    log_ok "리허설 성공: ${elapsed}s"

    # 마지막 리허설 마커
    date -u +'%Y-%m-%dT%H:%M:%SZ' > "${BACKUP_LOCAL_DIR}/.last_drill_success"
}

cleanup_stale_drill_dbs() {
    log_info "오래된 drill DB 정리 (24시간 이상)"
    local now_epoch yesterday_stamp
    yesterday_stamp=$(date -d '24 hours ago' +%Y%m%d_%H%M 2>/dev/null \
                   || date -v-24H +%Y%m%d_%H%M 2>/dev/null \
                   || echo "00000000_0000")

    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -At \
        -c "SELECT datname FROM pg_database WHERE datname LIKE 'tradepilot_drill_%'" \
        2>/dev/null | while read -r dbname; do
        local stamp="${dbname#tradepilot_drill_}"
        if [[ "${stamp}" < "${yesterday_stamp}" ]]; then
            log_info "  DROP ${dbname} (오래됨)"
            psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
                -c "DROP DATABASE IF EXISTS \"${dbname}\";" 2>/dev/null || true
        fi
    done
}

main "$@"
