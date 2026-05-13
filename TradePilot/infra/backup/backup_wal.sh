#!/usr/bin/env bash
# =====================================================================
# TradePilot PostgreSQL WAL 아카이빙 (archive_command)
# 파일: backup_wal.sh
# 목적:
#   1) PostgreSQL 가 호출하는 archive_command 구현
#   2) WAL 세그먼트를 로컬 디렉토리 + S3 로 이중 저장
#   3) 5분 단위 PITR 가능
#
# postgresql.conf 설정:
#   archive_mode = on
#   archive_command = '/opt/tradepilot/infra/backup/backup_wal.sh "%p" "%f"'
#   archive_timeout = 300   # 5분
#
# 인자 (PostgreSQL이 전달):
#   $1 = %p  WAL 파일의 절대 경로 (예: pg_wal/000000010000000000000023)
#   $2 = %f  WAL 파일명         (예: 000000010000000000000023)
#
# 종료코드:
#   0  성공  → PostgreSQL 이 WAL 파일 안전하게 폐기
#   비0    실패  → PostgreSQL 이 재시도 (DISK FULL 위험!)
#
# 의존성: cp, sha256sum, aws-cli/rclone, gpg(optional)
# =====================================================================

# WAL 아카이빙은 PostgreSQL 내부에서 빈번히 호출되므로
# 로깅을 최소화하고, 락 사용도 자제 (각 WAL 파일별 독립).
SCRIPT_NAME="backup_wal.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

# WAL 전용 로그(빈도 높음 → 별도 파일)
LOG_DIR="${BACKUP_LOCAL_DIR}/log"
mkdir -p "${LOG_DIR}"
WAL_LOG="${LOG_DIR}/wal_archive_$(date +%Y%m%d).log"

wal_log() {
    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WAL] $*" >> "${WAL_LOG}"
}

main() {
    local src_path="${1:?}"
    local wal_name="${2:?}"

    load_env >/dev/null 2>&1 || true
    : "${BACKUP_LOCAL_DIR:=/var/backup/tradepilot}"
    local wal_dir="${BACKUP_LOCAL_DIR}/wal"
    mkdir -p "${wal_dir}"

    local dest="${wal_dir}/${wal_name}"

    # ---- 1) 로컬 복사 (atomic: tmp → rename) ----------------------
    if [[ ! -f "${src_path}" ]]; then
        wal_log "ERROR src not found: ${src_path}"
        exit 1
    fi

    if [[ -f "${dest}" ]]; then
        # 이미 존재 → 동일 파일이면 OK, 다르면 거부 (PostgreSQL 안전 규약)
        if cmp -s "${src_path}" "${dest}"; then
            wal_log "SKIP already-archived: ${wal_name}"
            exit 0
        else
            wal_log "ERROR conflict: ${wal_name} differs from existing"
            exit 2
        fi
    fi

    cp -p "${src_path}" "${dest}.tmp" || { wal_log "ERROR cp failed: ${wal_name}"; exit 3; }
    mv -f "${dest}.tmp" "${dest}"     || { wal_log "ERROR mv failed: ${wal_name}"; exit 4; }

    # ---- 2) 체크섬 (.sha256, 빠른 검증용) -------------------------
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "${dest}" > "${dest}.sha256" 2>/dev/null || true
    fi

    # ---- 3) 옵션 압축 (WAL 16MB → ~5MB, 디스크 절약) --------------
    # gzip 사용시 PITR 복구 시 자동 해제 필요 → restore_command와 짝
    if command -v gzip >/dev/null 2>&1; then
        gzip -1 -f "${dest}" || wal_log "WARN gzip skipped: ${wal_name}"
        dest="${dest}.gz"
    fi

    # ---- 4) S3 업로드 (백그라운드 실행 옵션) ----------------------
    # PostgreSQL은 archive_command가 빠르게 끝나야 다음 WAL 진행 가능.
    # 동기 업로드는 네트워크 장애 시 archive_command가 막히는 위험.
    # → 로컬 복사 성공 후 즉시 0 반환, S3 업로드는 별도 sweep 스크립트로 처리 권장.
    # 다만 운영자 선택 가능하도록 WAL_S3_SYNC=true 일 때만 동기 업로드.
    if [[ "${WAL_S3_SYNC:-false}" == "true" ]] && [[ -n "${S3_BUCKET:-}" ]]; then
        if [[ -f "${dest}.sha256" ]]; then
            "${SCRIPT_DIR}/s3_upload.sh" "${dest}" "wal/" >/dev/null 2>&1 \
                || wal_log "WARN S3 upload failed (kept locally): ${wal_name}"
        fi
    fi

    wal_log "OK archived: ${wal_name} -> ${dest}"

    # 매 100번째 WAL마다 이벤트 발행(노이즈 감소)
    local count_file="${BACKUP_LOCAL_DIR}/.wal_count"
    local count=0
    [[ -f "${count_file}" ]] && count=$(cat "${count_file}")
    count=$((count + 1))
    echo "${count}" > "${count_file}"
    if (( count % 100 == 0 )); then
        emit_backup_event success wal "$(printf '{"wal_name":"%s","total_count":%s}' "${wal_name}" "${count}")" \
            >/dev/null 2>&1 || true
    fi

    # 마지막 아카이브 마커
    date -u +'%Y-%m-%dT%H:%M:%SZ' > "${BACKUP_LOCAL_DIR}/.last_wal_archive"
    echo "${wal_name}" >> "${BACKUP_LOCAL_DIR}/.last_wal_archive"

    exit 0
}

# PostgreSQL 호출은 인자 2개 필수
if [[ $# -lt 2 ]]; then
    cat <<EOF >&2
사용법: $0 <wal_path> <wal_name>
  PostgreSQL 의 archive_command 가 자동으로 호출함.
  postgresql.conf:
    archive_command = '/path/to/backup_wal.sh "%p" "%f"'
EOF
    exit 1
fi

main "$@"
