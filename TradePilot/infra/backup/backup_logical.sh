#!/usr/bin/env bash
# =====================================================================
# TradePilot PostgreSQL 논리 백업 (글로벌 객체: 롤/테이블스페이스/권한)
# 파일: backup_logical.sh
# 목적:
#   pg_dumpall --globals-only 로 ROLE/TABLESPACE/ACL 백업.
#   pg_dump 풀백업은 데이터베이스 단위라 글로벌 객체가 누락되므로
#   본 스크립트로 별도 백업하여 PITR/재구축 시 완전 복원 가능.
#
# 의존성: pg_dumpall, gzip, sha256sum
# 환경변수: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
# 사용법:
#   ./backup_logical.sh
#   ./backup_logical.sh --dry-run
#
# Cron 예: 매일 02:50 (풀백업 10분 전)
#   50 2 * * * /opt/tradepilot/infra/backup/backup_logical.sh
# =====================================================================

SCRIPT_NAME="backup_logical.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

NO_UPLOAD=false
while (( $# > 0 )); do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        --no-upload) NO_UPLOAD=true ;;
        -h|--help)
            cat <<EOF
사용법: $0 [--dry-run] [--no-upload]
  글로벌 객체(롤/테이블스페이스/ACL) 만 pg_dumpall 로 백업.
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
    acquire_lock backup_logical

    emit_backup_event started logical '{}'

    local out_dir="${BACKUP_LOCAL_DIR}/logical"
    mkdir -p "${out_dir}"

    local stamp
    stamp="$(date +%Y%m%d_%H%M%S)"
    local out_file="${out_dir}/globals_${stamp}.sql"

    log_info "pg_dumpall --globals-only 시작 → ${out_file}"

    # --globals-only: 데이터베이스 객체 제외, ROLE/TABLESPACE/ACL만
    if ! run_cmd pg_dumpall \
        -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
        --globals-only \
        --no-role-passwords \
        --file="${out_file}"; then
        log_error "pg_dumpall 실패"
        emit_backup_event failure logical '{"error":"pg_dumpall"}'
        emit_backup_alert CRITICAL "TradePilot 논리 백업 실패"
        exit 4
    fi

    if [[ "${DRY_RUN}" == "true" ]]; then
        emit_backup_event success logical '{"dry_run":true}'
        return 0
    fi

    # 압축
    run_cmd gzip -9 -f "${out_file}"
    out_file="${out_file}.gz"

    # 체크섬 + 암호화
    make_checksum "${out_file}"
    local final_file
    final_file="$(encrypt_file "${out_file}")"
    [[ "${final_file}" != "${out_file}" ]] && make_checksum "${final_file}"

    # S3 업로드
    if [[ "${NO_UPLOAD}" != "true" ]]; then
        "${SCRIPT_DIR}/s3_upload.sh" "${final_file}" "logical/" \
            || log_warn "S3 업로드 실패 (로컬 보존)"
    fi

    # 보존 정책
    find "${out_dir}" -maxdepth 1 -type f \
        \( -name 'globals_*.sql.gz*' -o -name 'globals_*.sha256' \) \
        -mtime "+${RETENTION_DAYS_LOCAL:-7}" -print -delete || true

    local size
    size=$(file_size_bytes "${final_file}")
    emit_backup_event success logical \
        "$(printf '{"file":"%s","bytes":%s}' "$(basename "${final_file}")" "${size}")"
    log_ok "논리 백업 완료: $(human_size "${size}")"
}

main "$@"
