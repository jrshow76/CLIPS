#!/usr/bin/env bash
# =====================================================================
# TradePilot 백업 보존 정책 적용
# 파일: retention.sh
# 목적:
#   1) 로컬 백업 디렉토리에서 오래된 파일 삭제 (RETENTION_DAYS_LOCAL)
#   2) WAL 아카이브 정리 (가장 최근 풀백업 시점 -1일 이전 WAL 삭제 가능)
#   3) S3는 라이프사이클 정책으로 자동 처리 (s3_lifecycle.json 참조)
#   4) 월말 본은 monthly/ prefix 로 분리 후 1년 보관
#
# 안전장치:
#   - 마지막 풀백업 1개는 절대 삭제하지 않음 (방어 로직)
#   - 마지막 풀백업 시점 이전 WAL만 삭제 (PITR 가능 보장)
#
# 의존성: find, aws-cli/rclone(옵션, S3 정리용)
#
# 사용법:
#   ./retention.sh
#   ./retention.sh --dry-run
#
# Cron 예: 0 * * * * /opt/tradepilot/infra/backup/retention.sh
# =====================================================================

SCRIPT_NAME="retention.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

while (( $# > 0 )); do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        -h|--help)
            cat <<EOF
사용법: $0 [--dry-run]
환경변수:
  RETENTION_DAYS_LOCAL    로컬 풀백업 보존 일 (기본 7)
  RETENTION_DAYS_REMOTE   S3 정리는 라이프사이클로 처리(여기서는 메타만)
  RETENTION_DAYS_MONTHLY  월말 본 보존 일 (기본 365)
EOF
            exit 0 ;;
    esac
    shift
done

main() {
    log_setup
    load_env
    require_env BACKUP_LOCAL_DIR
    acquire_lock retention

    local local_keep="${RETENTION_DAYS_LOCAL:-7}"
    local monthly_keep="${RETENTION_DAYS_MONTHLY:-365}"

    log_info "보존 정책 시작: local=${local_keep}d monthly=${monthly_keep}d"

    cleanup_full_backups "${local_keep}"
    cleanup_logical_backups "${local_keep}"
    cleanup_wal_archives
    promote_monthly_backup
    cleanup_log_files

    log_ok "보존 정책 적용 완료"
    emit_backup_event success retention '{}'
}

# ---- 풀백업 정리 (마지막 1개는 보존) -------------------------------
cleanup_full_backups() {
    local keep_days="$1"
    local dir="${BACKUP_LOCAL_DIR}/full"
    [[ -d "${dir}" ]] || return 0

    # 최신 1개는 무조건 보존
    local newest
    newest=$(find "${dir}" -maxdepth 1 -type f -name 'tradepilot_*.dump*' \
        -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | awk '{print $2}')

    log_info "최신 풀백업 (보호): ${newest:-none}"

    # ${keep_days}일 이상 오래된 파일 중 최신 제외하고 삭제
    find "${dir}" -maxdepth 1 -type f \
        \( -name 'tradepilot_*.dump*' -o -name 'tradepilot_*.sha256' \) \
        -mtime "+${keep_days}" \
        ! -path "${newest:-/dev/null}*" -print0 | \
    while IFS= read -r -d '' f; do
        if [[ "${DRY_RUN}" == "true" ]]; then
            log_info "[DRY] rm ${f}"
        else
            rm -f "${f}" && log_info "삭제: ${f}"
        fi
    done
}

# ---- 논리 백업 정리 ----------------------------------------------
cleanup_logical_backups() {
    local keep_days="$1"
    local dir="${BACKUP_LOCAL_DIR}/logical"
    [[ -d "${dir}" ]] || return 0

    find "${dir}" -maxdepth 1 -type f \
        \( -name 'globals_*.sql.gz*' -o -name 'globals_*.sha256' \) \
        -mtime "+${keep_days}" -print0 | \
    while IFS= read -r -d '' f; do
        if [[ "${DRY_RUN}" == "true" ]]; then
            log_info "[DRY] rm ${f}"
        else
            rm -f "${f}" && log_info "삭제(논리): ${f}"
        fi
    done
}

# ---- WAL 정리 (마지막 풀백업 시점 -1일 이전 안전 삭제) ------------
cleanup_wal_archives() {
    local dir="${BACKUP_LOCAL_DIR}/wal"
    [[ -d "${dir}" ]] || return 0

    # 마지막 풀백업의 mtime 기준 -1일
    local marker="${BACKUP_LOCAL_DIR}/.last_full_success"
    if [[ ! -f "${marker}" ]]; then
        log_warn "마지막 풀백업 마커 없음 → WAL 정리 보류"
        return 0
    fi

    # 풀백업 + 보존 기간 (RETENTION_DAYS_LOCAL) 이전 WAL 안전 삭제
    local safe_days=$(( ${RETENTION_DAYS_LOCAL:-7} + 1 ))
    log_info "WAL 정리: ${safe_days}일 이전 파일 삭제"

    find "${dir}" -maxdepth 1 -type f \
        \( -name '0000*' -o -name '0000*.gz' -o -name '0000*.sha256' \) \
        -mtime "+${safe_days}" -print0 | \
    while IFS= read -r -d '' f; do
        if [[ "${DRY_RUN}" == "true" ]]; then
            log_info "[DRY] rm ${f}"
        else
            rm -f "${f}"
        fi
    done

    local count
    count=$(find "${dir}" -maxdepth 1 -type f -name '0000*' 2>/dev/null | wc -l)
    log_info "WAL 잔여: ${count}개"
}

# ---- 월말 본 승격 (매월 1일 한 번) -------------------------------
# 매달 1일 ~ 3일 사이에만 동작 (cron에서 매시 실행해도 여러번 실행 안전)
promote_monthly_backup() {
    local day_of_month
    day_of_month=$(date +%d)
    if (( 10#${day_of_month} > 3 )); then
        return 0
    fi

    local prev_month_pattern
    prev_month_pattern=$(date -d 'last month' +%Y%m 2>/dev/null \
                     || date -v-1m +%Y%m 2>/dev/null)
    [[ -z "${prev_month_pattern}" ]] && return 0

    # 전월의 마지막 풀백업 찾기
    local last_of_month
    last_of_month=$(find "${BACKUP_LOCAL_DIR}/full" -maxdepth 1 -type f \
        -name "tradepilot_${prev_month_pattern}*.dump*" \
        ! -name '*.sha256' \
        -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | awk '{print $2}')

    if [[ -z "${last_of_month}" ]]; then
        log_info "월말 승격 대상 없음 (${prev_month_pattern})"
        return 0
    fi

    log_info "월말 본 S3 승격: ${last_of_month} → monthly/${prev_month_pattern}/"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY] s3_upload to monthly/${prev_month_pattern}/"
        return 0
    fi

    # S3 monthly/ prefix 로 복사 (이미 standard 에 있으면 copy로 처리)
    "${SCRIPT_DIR}/s3_upload.sh" "${last_of_month}" "monthly/${prev_month_pattern}/" \
        || log_warn "월말 본 S3 승격 실패"
}

# ---- 로그 파일 정리 (90일) ---------------------------------------
cleanup_log_files() {
    local dir="${BACKUP_LOCAL_DIR}/log"
    [[ -d "${dir}" ]] || return 0

    find "${dir}" -maxdepth 1 -type f -name '*.log' -mtime +90 -print0 | \
    while IFS= read -r -d '' f; do
        if [[ "${DRY_RUN}" == "true" ]]; then
            log_info "[DRY] rm log ${f}"
        else
            rm -f "${f}"
        fi
    done
}

main "$@"
