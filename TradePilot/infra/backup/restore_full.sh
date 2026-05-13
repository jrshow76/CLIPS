#!/usr/bin/env bash
# =====================================================================
# TradePilot PostgreSQL 풀백업 복구 (pg_restore)
# 파일: restore_full.sh
# 목적:
#   1) 백업 파일(GPG/age/평문) → 복호화 → 체크섬 검증
#   2) 대상 DB 존재 확인 + 사용자 명시 confirm
#   3) pg_restore -d <target> 로 복원
#   4) 복원 후 핵심 객체 카운트 출력
#
# 의존성: pg_restore, psql, gpg/age, sha256sum
#
# 환경변수: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, BACKUP_LOCAL_DIR
#
# 사용법:
#   ./restore_full.sh <backup_file> <target_db>
#   ./restore_full.sh /var/backup/tradepilot/full/tradepilot_20260513_030000.dump.gpg tradepilot_restore
#   ./restore_full.sh --yes <file> <target_db>     # 비대화형(스크립트용)
#   ./restore_full.sh --jobs 4 <file> <target_db>  # 병렬 복원
#
# 안전장치:
#   - 대상 DB가 운영 DB($DB_NAME)면 거부 (명시적 --force-prod 필요)
#   - 대상 DB 존재 시 기본 거부 (--drop-existing 옵션으로만 강제 삭제)
# =====================================================================

SCRIPT_NAME="restore_full.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ASSUME_YES=false
DROP_EXISTING=false
FORCE_PROD=false
JOBS=2
SCHEMA_ONLY=false

usage() {
    cat <<EOF
사용법: $0 [옵션] <backup_file> <target_db>

옵션:
  --yes               확인 프롬프트 생략 (자동화용)
  --drop-existing     대상 DB가 이미 존재하면 DROP 후 재생성
  --force-prod        대상이 운영 DB(\$DB_NAME)일 때 강제 진행 (위험!)
  --jobs N            pg_restore 병렬 복원 jobs (기본 2)
  --schema-only       스키마만 복원 (데이터 제외)
  -h, --help          도움말

예시:
  $0 --yes /var/backup/tradepilot/full/tradepilot_20260513_030000.dump.gpg tradepilot_drill
  $0 --drop-existing --jobs 4 backup.dump.gpg tradepilot_staging

주의:
  - 운영 DB 직접 복원은 \$DB_NAME 일치 시 차단된다 (--force-prod 로만 가능).
  - 복원 전 반드시 현재 DB의 풀백업을 별도로 확보하라.
EOF
}

# ---- 옵션 파싱 -----------------------------------------------------
POSITIONAL=()
while (( $# > 0 )); do
    case "$1" in
        --yes) ASSUME_YES=true ;;
        --drop-existing) DROP_EXISTING=true ;;
        --force-prod) FORCE_PROD=true ;;
        --jobs) shift; JOBS="$1" ;;
        --schema-only) SCHEMA_ONLY=true ;;
        --dry-run) DRY_RUN=true ;;
        -h|--help) usage; exit 0 ;;
        --) shift; while (( $# > 0 )); do POSITIONAL+=("$1"); shift; done; break ;;
        -*) log_error "알 수 없는 옵션: $1"; usage; exit 1 ;;
        *) POSITIONAL+=("$1") ;;
    esac
    shift
done

(( ${#POSITIONAL[@]} >= 2 )) || { usage; exit 1; }
BACKUP_FILE="${POSITIONAL[0]}"
TARGET_DB="${POSITIONAL[1]}"

main() {
    log_setup
    load_env
    require_env DB_HOST DB_PORT DB_USER
    export_pgpassword

    [[ -f "${BACKUP_FILE}" ]] || { log_error "백업 파일 없음: ${BACKUP_FILE}"; exit 2; }

    # ---- 운영 DB 보호 ----------------------------------------------
    if [[ "${TARGET_DB}" == "${DB_NAME:-}" ]] && [[ "${FORCE_PROD}" != "true" ]]; then
        log_error "대상이 운영 DB(${DB_NAME}) 입니다. --force-prod 없이는 거부."
        log_error "  → 임시 DB로 복원 후 검증하고 SWAP하는 절차를 권장합니다."
        exit 10
    fi

    # ---- 체크섬 검증 -----------------------------------------------
    if [[ -f "${BACKUP_FILE}.sha256" ]]; then
        log_info "체크섬 검증 시작"
        verify_checksum "${BACKUP_FILE}" || { log_error "체크섬 검증 실패"; exit 11; }
    else
        log_warn "체크섬 파일 없음: ${BACKUP_FILE}.sha256 (검증 생략)"
    fi

    # ---- 복호화 (필요 시) ------------------------------------------
    local work_dir
    work_dir="$(mktemp -d -t tp_restore_XXXXXX)"
    trap "rm -rf '${work_dir}'" EXIT

    local dump_file="${BACKUP_FILE}"
    case "${BACKUP_FILE}" in
        *.gpg|*.age)
            log_info "복호화 시작 → ${work_dir}"
            local plain_name
            plain_name="$(basename "${BACKUP_FILE%.gpg}")"
            plain_name="${plain_name%.age}"
            dump_file="${work_dir}/${plain_name}"
            decrypt_file "${BACKUP_FILE}" "${dump_file}" >/dev/null
            ;;
    esac

    log_info "백업 파일: ${dump_file} ($(human_size "$(file_size_bytes "${dump_file}")"))"

    # ---- 백업 파일 메타 출력 (TOC) ---------------------------------
    log_info "pg_restore TOC 미리보기 (head 20):"
    pg_restore -l "${dump_file}" 2>/dev/null | head -20 || true

    # ---- 사용자 확인 -----------------------------------------------
    if [[ "${ASSUME_YES}" != "true" ]]; then
        echo
        echo "[복원 계획]"
        echo "  대상 호스트 : ${DB_HOST}:${DB_PORT}"
        echo "  대상 DB     : ${TARGET_DB}"
        echo "  백업 파일   : ${BACKUP_FILE}"
        echo "  병렬 jobs   : ${JOBS}"
        echo "  스키마 전용 : ${SCHEMA_ONLY}"
        echo "  기존 DROP   : ${DROP_EXISTING}"
        echo
        read -r -p "정말 진행하시겠습니까? [yes/no]: " ans
        [[ "${ans}" == "yes" ]] || { log_warn "사용자 취소"; exit 0; }
    fi

    # ---- 대상 DB 존재 처리 -----------------------------------------
    local exists
    exists=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -At \
        -c "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}'")

    if [[ "${exists}" == "1" ]]; then
        if [[ "${DROP_EXISTING}" == "true" ]]; then
            log_warn "대상 DB 존재 → DROP 후 재생성"
            run_cmd psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
                -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${TARGET_DB}' AND pid<>pg_backend_pid();"
            run_cmd psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
                -c "DROP DATABASE \"${TARGET_DB}\";"
        else
            log_error "대상 DB(${TARGET_DB}) 가 이미 존재합니다. --drop-existing 옵션 필요."
            exit 12
        fi
    fi

    log_info "대상 DB 생성: ${TARGET_DB}"
    run_cmd psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
        -c "CREATE DATABASE \"${TARGET_DB}\" TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';"

    # ---- pg_restore --------------------------------------------------
    local pg_opts=(
        -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}"
        -d "${TARGET_DB}"
        --jobs="${JOBS}"
        --no-owner --no-privileges
        --verbose
    )
    [[ "${SCHEMA_ONLY}" == "true" ]] && pg_opts+=(--schema-only)

    log_info "pg_restore 시작 (jobs=${JOBS})"
    local started
    started=$(date +%s)

    if ! run_cmd pg_restore "${pg_opts[@]}" "${dump_file}"; then
        local rc=$?
        log_error "pg_restore 실패 (rc=${rc}) — 부분 복원이 발생했을 수 있음"
        exit "${rc}"
    fi

    local elapsed=$(( $(date +%s) - started ))
    log_ok "pg_restore 완료 (${elapsed}s)"

    # ---- 복원 후 검증 -----------------------------------------------
    log_info "복원 후 핵심 카운트:"
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${TARGET_DB}" -c "
        SELECT n.nspname AS schema, COUNT(*) AS tables
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind IN ('r','p')
           AND n.nspname LIKE 'tp_%'
         GROUP BY n.nspname ORDER BY n.nspname;
    " || true

    log_ok "복원 완료: ${TARGET_DB}"
    log_info "다음 단계 권장:"
    log_info "  1) drill_validation.sql 실행"
    log_info "  2) 권한(ROLE) 복원: psql -d ${TARGET_DB} -f globals_*.sql"
    log_info "  3) ANALYZE 실행: psql -d ${TARGET_DB} -c 'ANALYZE'"
}

main
