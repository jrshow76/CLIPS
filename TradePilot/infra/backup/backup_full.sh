#!/usr/bin/env bash
# =====================================================================
# TradePilot PostgreSQL 풀백업 (pg_dump custom format)
# 파일: backup_full.sh
# 목적:
#   1) pg_dump -Fc -Z9 로 풀백업 dump 생성
#   2) SHA256 체크섬 생성
#   3) GPG/age 암호화 (가능 시)
#   4) S3 호환 스토리지로 업로드
#   5) 로컬 보존 정책 적용 (RETENTION_DAYS_LOCAL)
#   6) Redis publish (tp:backup.event)
#
# 의존성:
#   - postgresql-client (pg_dump)
#   - gpg(or age), aws-cli(or rclone), redis-cli, jq, sha256sum
#
# 환경변수: .env.backup 참조
#
# 사용법:
#   BACKUP_ENV_FILE=/etc/tradepilot/.env.backup ./backup_full.sh
#   ./backup_full.sh --dry-run
#   ./backup_full.sh --no-upload  (S3 업로드 생략)
#
# Cron 예: 0 3 * * * /opt/tradepilot/infra/backup/backup_full.sh >> /var/log/tradepilot/backup.log 2>&1
# =====================================================================

SCRIPT_NAME="backup_full.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

# ---- 옵션 파싱 -----------------------------------------------------
NO_UPLOAD=false
EXTRA_PG_OPTS=()
while (( $# > 0 )); do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        --no-upload) NO_UPLOAD=true ;;
        --jobs) shift; PG_DUMP_JOBS="$1" ;;
        -h|--help)
            cat <<EOF
사용법: $0 [옵션]
  --dry-run     실제 명령은 실행하지 않고 출력만
  --no-upload   S3 업로드 생략 (로컬만)
  --jobs N      pg_dump 병렬 jobs (dir format에서만 의미)
EOF
            exit 0 ;;
        *) log_warn "알 수 없는 옵션: $1" ;;
    esac
    shift
done

main() {
    log_setup
    load_env
    require_env DB_HOST DB_PORT DB_USER DB_NAME BACKUP_LOCAL_DIR
    export_pgpassword
    acquire_lock backup_full

    local started_at
    started_at=$(date +%s)
    emit_backup_event started full '{}'

    local out_dir="${BACKUP_LOCAL_DIR}/full"
    mkdir -p "${out_dir}"
    require_free_space_mb "${out_dir}" 2048   # 풀백업 최소 2GB 여유 권장

    local stamp
    stamp="$(date +%Y%m%d_%H%M%S)"
    local base="${out_dir}/tradepilot_${stamp}"
    local dump_file="${base}.dump"

    # ---- pg_dump 옵션 구성 -----------------------------------------
    local pg_opts=(
        -h "${DB_HOST}"
        -p "${DB_PORT}"
        -U "${DB_USER}"
        -d "${DB_NAME}"
        -Fc                                     # custom format (pg_restore 가능)
        -Z "${PG_DUMP_COMPRESS_LEVEL:-9}"       # 최대 압축
        --no-owner                              # 복원 시 ROLE 의존 최소화
        --no-privileges                         # 권한은 backup_logical.sh로 별도
        --verbose
    )

    # 감사 스키마 제외 옵션
    if [[ "${EXCLUDE_AUDIT_SCHEMA:-false}" == "true" ]]; then
        pg_opts+=(--exclude-schema=tp_audit)
        log_info "tp_audit 스키마 제외 (별도 백업 권장)"
    fi

    pg_opts+=(-f "${dump_file}")

    # ---- 실행 -------------------------------------------------------
    log_info "pg_dump 시작 → ${dump_file}"
    local rc=0
    if ! run_cmd pg_dump "${pg_opts[@]}"; then
        rc=$?
        log_error "pg_dump 실패 (rc=${rc})"
        emit_backup_event failure full "$(printf '{"error":"pg_dump rc=%s"}' "${rc}")"
        emit_backup_alert CRITICAL "TradePilot 풀백업 실패: pg_dump rc=${rc}"
        exit "${rc}"
    fi

    # DRY_RUN 모드에선 dump 파일이 실제로 없으므로 후속 단계 스킵
    if [[ "${DRY_RUN}" == "true" ]]; then
        log_warn "DRY_RUN: 후속 단계(checksum/encrypt/upload) 생략"
        emit_backup_event success full '{"dry_run":true}'
        return 0
    fi

    local size_bytes
    size_bytes=$(file_size_bytes "${dump_file}")
    log_ok "pg_dump 완료: $(human_size "${size_bytes}")"

    # ---- 체크섬 -----------------------------------------------------
    make_checksum "${dump_file}"

    # ---- 암호화 -----------------------------------------------------
    local encrypted_file
    encrypted_file="$(encrypt_file "${dump_file}")"
    # 암호화 후 체크섬도 갱신 (S3에 함께 올림)
    if [[ "${encrypted_file}" != "${dump_file}" ]]; then
        make_checksum "${encrypted_file}"
        # 평문 .sha256은 정리 (암호화 파일 기준만 유지)
        rm -f "${dump_file}.sha256" 2>/dev/null || true
    fi

    local final_size
    final_size=$(file_size_bytes "${encrypted_file}")

    # ---- S3 업로드 --------------------------------------------------
    if [[ "${NO_UPLOAD}" == "true" ]]; then
        log_warn "--no-upload: S3 업로드 생략"
    else
        if "${SCRIPT_DIR}/s3_upload.sh" "${encrypted_file}" "full/"; then
            log_ok "S3 업로드 성공"
        else
            log_error "S3 업로드 실패 (로컬 백업은 보존)"
            emit_backup_alert WARN "TradePilot S3 업로드 실패: ${encrypted_file}"
        fi
    fi

    # ---- 로컬 보존 정책 (당일 이외 RETENTION_DAYS_LOCAL일 보관) ------
    local retain="${RETENTION_DAYS_LOCAL:-7}"
    log_info "로컬 보존 정책: ${retain}일 → 정리 시작"
    find "${out_dir}" -maxdepth 1 -type f \
        \( -name 'tradepilot_*.dump*' -o -name 'tradepilot_*.sha256' \) \
        -mtime "+${retain}" -print -delete || true

    # ---- 메타 기록 (마지막 성공 시각 마커) --------------------------
    date -u +'%Y-%m-%dT%H:%M:%SZ' > "${BACKUP_LOCAL_DIR}/.last_full_success"
    echo "${encrypted_file}"      >> "${BACKUP_LOCAL_DIR}/.last_full_success"

    local ended_at duration
    ended_at=$(date +%s)
    duration=$((ended_at - started_at))

    local extra
    extra=$(printf '{"file":"%s","bytes":%s,"duration_sec":%s,"compressed":true,"encrypted":%s}' \
        "$(basename "${encrypted_file}")" "${final_size}" "${duration}" \
        "$([[ "${encrypted_file}" != "${dump_file}" ]] && echo true || echo false)")

    emit_backup_event success full "${extra}"
    log_ok "풀백업 완료: $(human_size "${final_size}") / ${duration}s"
}

main "$@"
