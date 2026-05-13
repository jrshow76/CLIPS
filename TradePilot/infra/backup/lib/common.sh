#!/usr/bin/env bash
# =====================================================================
# TradePilot 백업 공통 라이브러리
# 파일: lib/common.sh
# 목적: 로깅, 환경변수 검증, 락, 알림, 암호화, 체크섬 공통 함수 제공
# 의존성: bash 4+, coreutils, openssl(or sha256sum), gpg(optional),
#         redis-cli(optional), aws-cli v2(optional)
# 사용법: 다른 스크립트에서 `source "$(dirname "$0")/lib/common.sh"`
# =====================================================================

# ---- 안전 모드 -----------------------------------------------------
set -Eeuo pipefail
IFS=$'\n\t'

# ---- 색상/포맷 (TTY일 때만) -----------------------------------------
if [[ -t 1 ]]; then
    readonly C_RED=$'\e[31m'
    readonly C_YELLOW=$'\e[33m'
    readonly C_GREEN=$'\e[32m'
    readonly C_BLUE=$'\e[34m'
    readonly C_RESET=$'\e[0m'
else
    readonly C_RED=""
    readonly C_YELLOW=""
    readonly C_GREEN=""
    readonly C_BLUE=""
    readonly C_RESET=""
fi

# ---- 전역 변수 ------------------------------------------------------
: "${BACKUP_LOCAL_DIR:=/var/backup/tradepilot}"
: "${LOCK_DIR:=${BACKUP_LOCAL_DIR}/.lock}"
: "${LOG_DIR:=${BACKUP_LOCAL_DIR}/log}"
: "${DRY_RUN:=false}"
: "${TZ:=Asia/Seoul}"
export TZ

# 호출 스크립트명(로깅용)
SCRIPT_NAME="${SCRIPT_NAME:-$(basename "${BASH_SOURCE[1]:-unknown}")}"
RUN_ID="$(date +%Y%m%d_%H%M%S)_$$"

# ---- 로깅 -----------------------------------------------------------
log_setup() {
    mkdir -p "${LOG_DIR}"
    LOG_FILE="${LOG_DIR}/${SCRIPT_NAME%.sh}_$(date +%Y%m%d).log"
    # tee로 stderr 듀얼 출력 (로그 파일 + 콘솔)
    exec > >(tee -a "${LOG_FILE}") 2>&1
}

_ts() { date +'%Y-%m-%d %H:%M:%S %Z'; }

log_info()  { echo "${C_BLUE}[INFO ]${C_RESET} $(_ts) [${SCRIPT_NAME}] $*"; }
log_warn()  { echo "${C_YELLOW}[WARN ]${C_RESET} $(_ts) [${SCRIPT_NAME}] $*" >&2; }
log_error() { echo "${C_RED}[ERROR]${C_RESET} $(_ts) [${SCRIPT_NAME}] $*" >&2; }
log_ok()    { echo "${C_GREEN}[ OK  ]${C_RESET} $(_ts) [${SCRIPT_NAME}] $*"; }

# ---- 환경변수 검증 --------------------------------------------------
# 사용: require_env DB_HOST DB_USER DB_NAME ...
require_env() {
    local missing=()
    local var
    for var in "$@"; do
        if [[ -z "${!var:-}" ]]; then
            missing+=("$var")
        fi
    done
    if (( ${#missing[@]} > 0 )); then
        log_error "필수 환경변수 누락: ${missing[*]}"
        log_error "  → .env.backup 파일을 확인하거나 export 후 재시도"
        exit 2
    fi
}

# ---- .env.backup 로드 ----------------------------------------------
# 사용: load_env [경로]
load_env() {
    local env_file="${1:-${BACKUP_ENV_FILE:-/etc/tradepilot/.env.backup}}"
    if [[ -f "${env_file}" ]]; then
        # shellcheck disable=SC1090
        set -a; source "${env_file}"; set +a
        log_info ".env.backup 로드: ${env_file}"
    else
        log_warn ".env.backup 미발견: ${env_file} (환경변수가 export 되어있는지 확인)"
    fi
}

# ---- 락 (동시 실행 방지) -------------------------------------------
LOCK_FD=""
LOCK_PATH=""
acquire_lock() {
    local lock_name="${1:-${SCRIPT_NAME%.sh}}"
    mkdir -p "${LOCK_DIR}"
    LOCK_PATH="${LOCK_DIR}/${lock_name}.lock"
    exec {LOCK_FD}>"${LOCK_PATH}"
    if ! flock -n "${LOCK_FD}"; then
        log_error "이미 실행 중: ${LOCK_PATH}"
        exit 3
    fi
    echo "$$" >&"${LOCK_FD}"
    log_info "락 획득: ${LOCK_PATH} (fd=${LOCK_FD})"
}

release_lock() {
    if [[ -n "${LOCK_FD}" ]]; then
        flock -u "${LOCK_FD}" 2>/dev/null || true
        eval "exec ${LOCK_FD}>&-"
        rm -f "${LOCK_PATH}" 2>/dev/null || true
    fi
}

# ---- DRY_RUN 래퍼 ---------------------------------------------------
# 사용: run_cmd pg_dump -h ... -f ...
run_cmd() {
    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY] $*"
        return 0
    fi
    log_info "RUN: $*"
    "$@"
}

# ---- SHA256 체크섬 --------------------------------------------------
# 사용: make_checksum <file>
make_checksum() {
    local f="$1"
    [[ -f "$f" ]] || { log_error "파일 없음: $f"; return 1; }
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$f" > "${f}.sha256"
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$f" > "${f}.sha256"
    else
        log_error "sha256sum/shasum 모두 미설치"
        return 1
    fi
    log_ok "체크섬 생성: ${f}.sha256"
}

verify_checksum() {
    local f="$1"
    [[ -f "${f}.sha256" ]] || { log_error "체크섬 파일 없음: ${f}.sha256"; return 1; }
    if command -v sha256sum >/dev/null 2>&1; then
        ( cd "$(dirname "$f")" && sha256sum -c "$(basename "${f}.sha256")" )
    else
        local expected actual
        expected="$(awk '{print $1}' "${f}.sha256")"
        actual="$(shasum -a 256 "$f" | awk '{print $1}')"
        [[ "${expected}" == "${actual}" ]] || { log_error "체크섬 불일치"; return 1; }
    fi
    log_ok "체크섬 검증 성공: ${f}"
}

# ---- 암호화 (GPG 우선, age 차순, 둘 다 없으면 평문 + 경고) ---------
# 사용: encrypt_file <input>  (output은 .gpg 또는 .age 확장자 추가)
encrypt_file() {
    local input="$1"
    if [[ -n "${GPG_RECIPIENT:-}" ]] && command -v gpg >/dev/null 2>&1; then
        local output="${input}.gpg"
        run_cmd gpg --batch --yes --trust-model always \
            --recipient "${GPG_RECIPIENT}" \
            --output "${output}" \
            --encrypt "${input}"
        rm -f "${input}"
        log_ok "GPG 암호화 완료: ${output}"
        echo "${output}"
    elif [[ -n "${AGE_RECIPIENT:-}" ]] && command -v age >/dev/null 2>&1; then
        local output="${input}.age"
        run_cmd age -r "${AGE_RECIPIENT}" -o "${output}" "${input}"
        rm -f "${input}"
        log_ok "age 암호화 완료: ${output}"
        echo "${output}"
    else
        if [[ "${ALLOW_PLAINTEXT_BACKUP:-false}" != "true" ]]; then
            log_error "암호화 키 미설정(GPG/age) + ALLOW_PLAINTEXT_BACKUP=false → 거부"
            log_error "  → .env.backup에 GPG_RECIPIENT 또는 AGE_RECIPIENT 설정 필요"
            return 4
        fi
        log_warn "평문 백업 사용 중 (운영환경 금지!) - ALLOW_PLAINTEXT_BACKUP=true"
        echo "${input}"
    fi
}

decrypt_file() {
    local input="$1"
    local output="${2:-}"
    case "${input}" in
        *.gpg)
            output="${output:-${input%.gpg}}"
            run_cmd gpg --batch --yes --decrypt --output "${output}" "${input}"
            ;;
        *.age)
            output="${output:-${input%.age}}"
            run_cmd age -d -i "${AGE_IDENTITY:?AGE_IDENTITY 미설정}" -o "${output}" "${input}"
            ;;
        *)
            output="${input}"
            ;;
    esac
    echo "${output}"
}

# ---- Redis 알림 -----------------------------------------------------
# 사용: redis_publish <channel> <json_payload>
redis_publish() {
    local channel="$1"
    local payload="$2"
    if [[ -z "${REDIS_URL:-}" ]]; then
        log_warn "REDIS_URL 미설정 → publish 건너뜀"
        return 0
    fi
    if ! command -v redis-cli >/dev/null 2>&1; then
        log_warn "redis-cli 미설치 → publish 건너뜀"
        return 0
    fi
    # DRY_RUN이어도 알림은 보낸다(테스트 시 의도적으로 건너뛰려면 별도 옵션)
    local n
    n=$(redis-cli -u "${REDIS_URL}" PUBLISH "${channel}" "${payload}" 2>&1) || {
        log_warn "Redis publish 실패: ${n}"
        return 0
    }
    log_info "Redis publish: ${channel} → ${n} subscribers"
}

emit_backup_event() {
    local status="$1"   # success | failure | started
    local kind="$2"     # full | wal | logical | drill | retention
    local extra_json="${3:-{}}"
    local channel="${REDIS_BACKUP_EVENT_CHANNEL:-tp:backup.event}"
    local host
    host="$(hostname -s 2>/dev/null || echo unknown)"
    local payload
    payload=$(printf '{"ts":"%s","host":"%s","script":"%s","run_id":"%s","kind":"%s","status":"%s","extra":%s}' \
        "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "${host}" "${SCRIPT_NAME}" "${RUN_ID}" "${kind}" "${status}" "${extra_json}")
    redis_publish "${channel}" "${payload}"
}

emit_backup_alert() {
    local severity="$1" # WARN | CRITICAL
    local message="$2"
    local channel="${REDIS_BACKUP_ALERT_CHANNEL:-tp:backup.alerts}"
    local payload
    payload=$(printf '{"ts":"%s","severity":"%s","script":"%s","run_id":"%s","message":%s}' \
        "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "${severity}" "${SCRIPT_NAME}" "${RUN_ID}" \
        "$(printf '%s' "${message}" | jq -Rs . 2>/dev/null || printf '"%s"' "${message//\"/\\\"}")")
    redis_publish "${channel}" "${payload}"
}

# ---- 사람이 읽기 쉬운 크기 -----------------------------------------
human_size() {
    local bytes="${1:-0}"
    if command -v numfmt >/dev/null 2>&1; then
        numfmt --to=iec-i --suffix=B --format='%.2f' "${bytes}"
    else
        awk -v b="${bytes}" 'BEGIN{
            split("B KB MB GB TB PB",u," ");
            i=1; while(b>=1024 && i<6){b/=1024;i++}
            printf "%.2f %s",b,u[i]
        }'
    fi
}

file_size_bytes() {
    local f="$1"
    if [[ -f "$f" ]]; then
        stat -c '%s' "$f" 2>/dev/null || stat -f '%z' "$f" 2>/dev/null || echo 0
    else
        echo 0
    fi
}

# ---- 종료 트랩 ------------------------------------------------------
on_exit() {
    local rc=$?
    release_lock
    if (( rc != 0 )); then
        log_error "스크립트 비정상 종료 (exit=${rc})"
    fi
    return ${rc}
}

trap on_exit EXIT
trap 'log_error "신호 수신 → 정리 후 종료"; exit 130' INT TERM

# ---- libpq 비밀번호 환경변수 ---------------------------------------
# pg_dump/pg_restore/psql 호출 시 ~/.pgpass 보다 우선
export_pgpassword() {
    if [[ -n "${DB_PASSWORD:-}" ]]; then
        export PGPASSWORD="${DB_PASSWORD}"
    fi
    if [[ -n "${DB_BACKUP_PASSWORD:-}" ]]; then
        export PGPASSWORD="${DB_BACKUP_PASSWORD}"
    fi
}

# ---- 디스크 공간 체크 ----------------------------------------------
require_free_space_mb() {
    local path="$1"
    local need_mb="$2"
    local free_kb
    free_kb=$(df -k "${path}" | awk 'NR==2 {print $4}')
    local free_mb=$((free_kb / 1024))
    if (( free_mb < need_mb )); then
        log_error "디스크 부족: ${path} 여유 ${free_mb}MB < 요구 ${need_mb}MB"
        return 1
    fi
    log_info "디스크 여유 OK: ${path} ${free_mb}MB"
}
