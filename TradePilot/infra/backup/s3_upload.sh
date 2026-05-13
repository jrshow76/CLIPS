#!/usr/bin/env bash
# =====================================================================
# TradePilot S3 업로드 래퍼
# 파일: s3_upload.sh
# 목적: aws-cli(S3) 또는 rclone(S3 호환)로 백업 파일 업로드
# 의존성: aws-cli v2 또는 rclone (S3_ENDPOINT 설정 시 rclone 권장)
# 환경변수:
#   S3_BUCKET, S3_REGION, S3_PREFIX, S3_STORAGE_CLASS
#   S3_ENDPOINT (R2/MinIO 호환 사용 시)
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (또는 IAM Role)
# 사용법:
#   ./s3_upload.sh <local_file> [remote_subpath]
#   ./s3_upload.sh /var/backup/tradepilot/full/x.dump.gpg full/
# =====================================================================

SCRIPT_NAME="s3_upload.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
    cat <<EOF
사용법: $0 <local_file_or_dir> [remote_subpath]
  local_file_or_dir : 업로드할 로컬 파일 또는 디렉토리
  remote_subpath    : S3_PREFIX 하위 경로(슬래시로 끝). 미지정 시 파일명 유지.

예:
  $0 /var/backup/tradepilot/full/tradepilot_20260513_030000.dump.gpg full/
  $0 /var/backup/tradepilot/wal/                                       wal/
EOF
}

main() {
    [[ $# -ge 1 ]] || { usage; exit 1; }
    local src="$1"
    local sub="${2:-}"

    load_env
    require_env S3_BUCKET S3_REGION

    [[ -e "${src}" ]] || { log_error "파일/디렉토리 없음: ${src}"; exit 1; }

    local prefix="${S3_PREFIX:-tradepilot/postgres}"
    local s3_path="s3://${S3_BUCKET}/${prefix}/${sub}"
    local storage_class="${S3_STORAGE_CLASS:-STANDARD_IA}"

    # rclone 사용 조건: S3_ENDPOINT 가 설정됐고 rclone 사용 가능
    if [[ -n "${S3_ENDPOINT:-}" ]] && command -v rclone >/dev/null 2>&1; then
        upload_with_rclone "${src}" "${sub}" "${storage_class}"
    elif command -v aws >/dev/null 2>&1; then
        upload_with_aws_cli "${src}" "${s3_path}" "${storage_class}"
    else
        log_error "aws-cli 와 rclone 모두 미설치"
        exit 5
    fi
}

upload_with_aws_cli() {
    local src="$1"
    local s3_path="$2"
    local storage_class="$3"

    local extra=()
    extra+=(--region "${S3_REGION}")
    extra+=(--storage-class "${storage_class}")
    extra+=(--only-show-errors)

    if [[ -d "${src}" ]]; then
        run_cmd aws s3 sync "${src}" "${s3_path}" "${extra[@]}"
    else
        # 파일 단일 업로드(파일명 유지)
        local target="${s3_path}$(basename "${src}")"
        run_cmd aws s3 cp "${src}" "${target}" "${extra[@]}"
        # 체크섬도 함께 업로드
        if [[ -f "${src}.sha256" ]]; then
            run_cmd aws s3 cp "${src}.sha256" "${target}.sha256" "${extra[@]}"
        fi
    fi
    log_ok "S3 업로드 완료: ${s3_path}"
}

upload_with_rclone() {
    local src="$1"
    local sub="$2"
    local storage_class="$3"

    # rclone 즉석 설정(stdin 파라미터)
    local remote="tps3"
    local args=()
    args+=(--s3-provider AWS)
    args+=(--s3-region "${S3_REGION}")
    args+=(--s3-storage-class "${storage_class}")
    if [[ -n "${S3_ENDPOINT:-}" ]]; then
        args+=(--s3-endpoint "${S3_ENDPOINT}")
        args+=(--s3-provider Other)
    fi
    args+=(--s3-access-key-id "${AWS_ACCESS_KEY_ID:-}")
    args+=(--s3-secret-access-key "${AWS_SECRET_ACCESS_KEY:-}")

    local dest=":s3:${S3_BUCKET}/${S3_PREFIX:-tradepilot/postgres}/${sub}"

    if [[ -d "${src}" ]]; then
        run_cmd rclone sync "${src}" "${dest}" "${args[@]}"
    else
        run_cmd rclone copy "${src}" "${dest}" "${args[@]}"
        [[ -f "${src}.sha256" ]] && run_cmd rclone copy "${src}.sha256" "${dest}" "${args[@]}"
    fi
    log_ok "rclone 업로드 완료: ${dest}"
}

main "$@"
