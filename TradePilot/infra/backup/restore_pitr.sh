#!/usr/bin/env bash
# =====================================================================
# TradePilot PostgreSQL PITR (Point-In-Time Recovery)
# 파일: restore_pitr.sh
# 목적:
#   1) 베이스 백업(pg_basebackup 디렉토리) 압축 풀기
#   2) WAL 아카이브 디렉토리 마운트
#   3) postgresql.auto.conf + recovery.signal 자동 생성
#   4) 임시 PGDATA 로 PostgreSQL 기동 → 복구 시점 도달 후 promote
#
# 의존성: tar, postgresql-server, gzip, gpg/age
#
# 환경변수:
#   PG_BIN            (예: /usr/lib/postgresql/15/bin)
#   PG_RECOVERY_PORT  (복구용 임시 포트, 기본 5433)
#   BACKUP_LOCAL_DIR  WAL 아카이브 위치
#
# 사용법:
#   ./restore_pitr.sh \
#     --base /var/backup/tradepilot/basebackup/2026-05-13 \
#     --wal-dir /var/backup/tradepilot/wal \
#     --target-time '2026-05-13 14:30:00 KST' \
#     --pgdata /tmp/tp_pitr_pgdata
#
#   --target-name 또는 --target-xid 옵션도 지원
#
# 산출물:
#   ${PGDATA} 에 복구 완료된 클러스터. 검증 후 운영 PGDATA 와 SWAP 또는
#   pg_dump로 다시 추출하여 운영 DB에 적용.
# =====================================================================

SCRIPT_NAME="restore_pitr.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

BASE_BACKUP=""
WAL_DIR=""
TARGET_TIME=""
TARGET_NAME=""
TARGET_XID=""
PGDATA=""
PG_RECOVERY_PORT="${PG_RECOVERY_PORT:-5433}"
PG_BIN="${PG_BIN:-/usr/lib/postgresql/15/bin}"
ASSUME_YES=false

usage() {
    cat <<EOF
사용법: $0 [옵션]
  --base <path>           베이스 백업 경로 (디렉토리 또는 .tar.gz)
  --wal-dir <path>        WAL 아카이브 디렉토리
  --target-time <ts>      복구 시점 (예: '2026-05-13 14:30:00 KST')
  --target-name <name>    명명된 복구 지점
  --target-xid <xid>      트랜잭션 ID
  --pgdata <path>         복구용 임시 PGDATA (없으면 생성)
  --port <port>           임시 포트 (기본 5433)
  --pg-bin <dir>          PostgreSQL bin 디렉토리
  --yes                   확인 프롬프트 생략

예:
  $0 --base /var/backup/tradepilot/basebackup/latest.tar.gz \\
     --wal-dir /var/backup/tradepilot/wal \\
     --target-time '2026-05-13 14:30:00 KST' \\
     --pgdata /tmp/tp_pitr_pgdata
EOF
}

while (( $# > 0 )); do
    case "$1" in
        --base) shift; BASE_BACKUP="$1" ;;
        --wal-dir) shift; WAL_DIR="$1" ;;
        --target-time) shift; TARGET_TIME="$1" ;;
        --target-name) shift; TARGET_NAME="$1" ;;
        --target-xid) shift; TARGET_XID="$1" ;;
        --pgdata) shift; PGDATA="$1" ;;
        --port) shift; PG_RECOVERY_PORT="$1" ;;
        --pg-bin) shift; PG_BIN="$1" ;;
        --yes) ASSUME_YES=true ;;
        --dry-run) DRY_RUN=true ;;
        -h|--help) usage; exit 0 ;;
        *) log_error "알 수 없는 옵션: $1"; usage; exit 1 ;;
    esac
    shift
done

main() {
    log_setup
    load_env

    [[ -n "${BASE_BACKUP}" ]] || { log_error "--base 필수"; usage; exit 1; }
    [[ -n "${WAL_DIR}" ]]     || { log_error "--wal-dir 필수"; usage; exit 1; }
    [[ -n "${PGDATA}" ]]      || { log_error "--pgdata 필수"; usage; exit 1; }

    # 복구 대상은 셋 중 하나 필수
    local targets=0
    [[ -n "${TARGET_TIME}" ]] && targets=$((targets+1))
    [[ -n "${TARGET_NAME}" ]] && targets=$((targets+1))
    [[ -n "${TARGET_XID}"  ]] && targets=$((targets+1))
    if (( targets == 0 )); then
        log_error "--target-time / --target-name / --target-xid 중 하나는 필수"
        exit 1
    fi
    if (( targets > 1 )); then
        log_error "복구 대상 옵션은 하나만 지정"
        exit 1
    fi

    # ---- 사용자 확인 ----
    if [[ "${ASSUME_YES}" != "true" ]]; then
        echo
        echo "[PITR 복구 계획]"
        echo "  베이스 백업 : ${BASE_BACKUP}"
        echo "  WAL 디렉토리: ${WAL_DIR}"
        echo "  PGDATA      : ${PGDATA}"
        echo "  포트        : ${PG_RECOVERY_PORT}"
        echo "  대상 시점   : ${TARGET_TIME:-${TARGET_NAME:-${TARGET_XID}}}"
        echo
        read -r -p "진행하시겠습니까? [yes/no]: " ans
        [[ "${ans}" == "yes" ]] || { log_warn "사용자 취소"; exit 0; }
    fi

    # ---- PGDATA 준비 ----
    if [[ -d "${PGDATA}" ]] && [[ -n "$(ls -A "${PGDATA}" 2>/dev/null)" ]]; then
        log_error "PGDATA가 비어있지 않습니다: ${PGDATA}"
        log_error "  → 다른 경로 사용 또는 명시적 삭제 후 재시도"
        exit 13
    fi
    run_cmd mkdir -p "${PGDATA}"
    run_cmd chmod 0700 "${PGDATA}"

    # ---- 베이스 백업 펼치기 ----
    if [[ -d "${BASE_BACKUP}" ]]; then
        log_info "베이스 백업 디렉토리 → 복사"
        run_cmd cp -a "${BASE_BACKUP}/." "${PGDATA}/"
    elif [[ -f "${BASE_BACKUP}" ]]; then
        log_info "베이스 백업 아카이브 → 압축 해제"
        case "${BASE_BACKUP}" in
            *.tar.gz|*.tgz) run_cmd tar -xzf "${BASE_BACKUP}" -C "${PGDATA}" ;;
            *.tar)          run_cmd tar -xf "${BASE_BACKUP}"  -C "${PGDATA}" ;;
            *) log_error "지원하지 않는 베이스 백업 형식: ${BASE_BACKUP}"; exit 14 ;;
        esac
    else
        log_error "베이스 백업 경로 없음: ${BASE_BACKUP}"
        exit 15
    fi

    # ---- recovery 설정 작성 ----
    local recovery_conf="${PGDATA}/postgresql.auto.conf"
    log_info "복구 설정 작성: ${recovery_conf}"

    {
        echo "# === TradePilot PITR auto-generated ==="
        echo "port = ${PG_RECOVERY_PORT}"
        echo "listen_addresses = 'localhost'"
        echo "# WAL 아카이브에서 가져오는 명령"
        # gzip 처리: backup_wal.sh 가 .gz 로 저장한다고 가정
        echo "restore_command = 'cp ${WAL_DIR}/%f.gz /tmp/%f.gz && gunzip -f /tmp/%f.gz && mv /tmp/%f %p || cp ${WAL_DIR}/%f %p'"
        echo "recovery_target_action = 'pause'"
        if [[ -n "${TARGET_TIME}" ]]; then
            echo "recovery_target_time = '${TARGET_TIME}'"
        elif [[ -n "${TARGET_NAME}" ]]; then
            echo "recovery_target_name = '${TARGET_NAME}'"
        elif [[ -n "${TARGET_XID}" ]]; then
            echo "recovery_target_xid = '${TARGET_XID}'"
        fi
        echo "recovery_target_inclusive = on"
        echo "# 복구 후 안전 정지(promote는 운영자가 수동으로 수행)"
    } >> "${recovery_conf}"

    # PostgreSQL 12+ : recovery.signal 파일로 PITR 모드 진입
    run_cmd touch "${PGDATA}/recovery.signal"

    # postmaster.pid 잔재 제거 (베이스백업에 포함되어있을 수 있음)
    rm -f "${PGDATA}/postmaster.pid" 2>/dev/null || true

    # ---- 시작 ----
    log_info "PostgreSQL 복구 시작 (포트 ${PG_RECOVERY_PORT})"
    log_info "  로그 파일: ${PGDATA}/log/startup.log (실시간 추적)"
    mkdir -p "${PGDATA}/log"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_warn "DRY_RUN: pg_ctl start 생략"
        return 0
    fi

    "${PG_BIN}/pg_ctl" -D "${PGDATA}" -l "${PGDATA}/log/startup.log" start

    log_ok "PITR 모드 진입. 복구 진행 상황:"
    log_info "  tail -f ${PGDATA}/log/startup.log"
    echo
    cat <<EOF
[다음 절차]
  1) 복구 완료 대기 (recovery_target_action=pause):
       psql -h localhost -p ${PG_RECOVERY_PORT} -d postgres \\
            -c "SELECT pg_is_in_recovery(), pg_last_wal_replay_lsn();"
  2) 데이터 검증 (drill_validation.sql 등):
       psql -h localhost -p ${PG_RECOVERY_PORT} -d ${DB_NAME:-tradepilot} \\
            -f ${SCRIPT_DIR}/drill_validation.sql
  3) 검증 OK → promote:
       ${PG_BIN}/pg_ctl -D ${PGDATA} promote
  4) 검증 실패 → 정지 후 다른 시점으로 재시도:
       ${PG_BIN}/pg_ctl -D ${PGDATA} stop -m fast
EOF
}

main
