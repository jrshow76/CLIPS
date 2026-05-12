#!/usr/bin/env bash
# =============================================================================
# 일일 헬스 체크 스크립트
# - 게이트웨이 ping (/healthz, /readyz)
# - 백엔드 ping (/health)
# - DB 백업 상태
# - Celery 큐 적체
# - Redis 메모리
# - 디스크 여유
#
# 실행: ./scripts/daily_health_check.sh
# 종료 코드: 0=정상, 1=경고, 2=Critical
# =============================================================================

set -u

# ---- 환경 설정 (override 가능) ----
GATEWAY_URL="${GATEWAY_URL:-http://localhost:9100}"
GATEWAY_API_KEY="${CREON_GATEWAY_API_KEY:-replace-me}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
DB_URL="${DATABASE_URL:-postgresql://tradepilot:tradepilot@localhost:5432/tradepilot}"

# 임계값
DISK_THRESHOLD_PCT=20
REDIS_MEM_THRESHOLD_PCT=70
CELERY_QUEUE_THRESHOLD=100
BACKUP_MAX_AGE_HOURS=24

EXIT_CODE=0
WARNINGS=()
ERRORS=()

# ---- 색상 ----
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

ok() {    echo -e "${GREEN}[OK]${NC} $1"; }
warn() {  echo -e "${YELLOW}[WARN]${NC} $1"; WARNINGS+=("$1"); EXIT_CODE=$((EXIT_CODE | 1)); }
fail() {  echo -e "${RED}[FAIL]${NC} $1"; ERRORS+=("$1"); EXIT_CODE=$((EXIT_CODE | 2)); }

# =============================================================================
# 1. 게이트웨이 헬스
# =============================================================================
echo "===== 1. 게이트웨이 헬스 ====="
if ! curl -sf --max-time 5 "${GATEWAY_URL}/healthz" > /tmp/gw_health.json; then
    fail "게이트웨이 /healthz 응답 없음 (${GATEWAY_URL})"
else
    TRADE_ENV=$(jq -r '.trade_env // "UNKNOWN"' < /tmp/gw_health.json)
    ok "게이트웨이 살아있음 (trade_env=${TRADE_ENV})"
fi

if curl -sf --max-time 5 "${GATEWAY_URL}/readyz" > /tmp/gw_ready.json; then
    COM=$(jq -r '.com_connected' < /tmp/gw_ready.json)
    ACC=$(jq -r '.account_loaded' < /tmp/gw_ready.json)
    if [[ "$COM" == "true" && "$ACC" == "true" ]]; then
        ok "게이트웨이 ready (COM=ok, account=ok)"
    else
        fail "게이트웨이 not ready (com_connected=$COM, account_loaded=$ACC)"
    fi
else
    fail "게이트웨이 /readyz 응답 없음"
fi

# 상세 상태 (인증 필요)
if [[ "$GATEWAY_API_KEY" != "replace-me" ]]; then
    if curl -sf --max-time 5 \
            -H "X-Gateway-Api-Key: $GATEWAY_API_KEY" \
            "${GATEWAY_URL}/system/status" > /tmp/gw_status.json; then
        RPS=$(jq -r '.data.request_count_1s' < /tmp/gw_status.json)
        LIMIT=$(jq -r '.data.rate_limit_per_sec' < /tmp/gw_status.json)
        ok "게이트웨이 RPS=${RPS}/${LIMIT}"
    else
        warn "게이트웨이 /system/status 호출 실패 (API key 확인 필요)"
    fi
fi

# =============================================================================
# 2. 백엔드 헬스
# =============================================================================
echo "===== 2. 백엔드 헬스 ====="
if curl -sf --max-time 5 "${BACKEND_URL}/api/v1/health" > /tmp/be_health.json 2>/dev/null \
   || curl -sf --max-time 5 "${BACKEND_URL}/health" > /tmp/be_health.json 2>/dev/null; then
    ok "백엔드 응답 정상"
else
    fail "백엔드 헬스 응답 없음"
fi

# =============================================================================
# 3. Redis 메모리
# =============================================================================
echo "===== 3. Redis ====="
if command -v redis-cli >/dev/null 2>&1; then
    REDIS_HOST=$(echo "$REDIS_URL" | sed -E 's#redis://([^:/]+).*#\1#')
    REDIS_PORT=$(echo "$REDIS_URL" | sed -E 's#redis://[^:]+:([0-9]+).*#\1#')
    REDIS_PORT="${REDIS_PORT:-6379}"

    if MEM_INFO=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" INFO memory 2>/dev/null); then
        USED=$(echo "$MEM_INFO" | grep '^used_memory:' | cut -d: -f2 | tr -d '\r')
        MAX=$(echo "$MEM_INFO" | grep '^maxmemory:' | cut -d: -f2 | tr -d '\r')
        if [[ -n "$MAX" && "$MAX" -gt 0 ]]; then
            PCT=$((USED * 100 / MAX))
            if [[ $PCT -lt $REDIS_MEM_THRESHOLD_PCT ]]; then
                ok "Redis 메모리 ${PCT}% (한도 ${REDIS_MEM_THRESHOLD_PCT}%)"
            else
                warn "Redis 메모리 ${PCT}% (한도 ${REDIS_MEM_THRESHOLD_PCT}% 초과)"
            fi
        else
            ok "Redis 정상 (사용량=${USED} bytes, maxmemory 미설정)"
        fi
    else
        warn "redis-cli 연결 실패"
    fi
else
    warn "redis-cli 미설치 (skip)"
fi

# =============================================================================
# 4. Celery 큐 적체
# =============================================================================
echo "===== 4. Celery 큐 ====="
if command -v redis-cli >/dev/null 2>&1; then
    for QUEUE in orders signals notifications celery; do
        LEN=$(redis-cli -h "${REDIS_HOST:-localhost}" -p "${REDIS_PORT:-6379}" \
              LLEN "$QUEUE" 2>/dev/null || echo "0")
        LEN="${LEN:-0}"
        if [[ "$LEN" -lt $CELERY_QUEUE_THRESHOLD ]]; then
            ok "큐 ${QUEUE} 적체 ${LEN}건"
        else
            warn "큐 ${QUEUE} 적체 ${LEN}건 (한도 ${CELERY_QUEUE_THRESHOLD})"
        fi
    done
fi

# =============================================================================
# 5. 디스크 여유
# =============================================================================
echo "===== 5. 디스크 ====="
DISK_AVAIL_PCT=$(df / | awk 'NR==2 {gsub("%","",$5); print 100-$5}')
if [[ $DISK_AVAIL_PCT -ge $DISK_THRESHOLD_PCT ]]; then
    ok "디스크 여유 ${DISK_AVAIL_PCT}% (한도 ${DISK_THRESHOLD_PCT}%)"
else
    fail "디스크 여유 ${DISK_AVAIL_PCT}% (한도 ${DISK_THRESHOLD_PCT}% 미만)"
fi

# =============================================================================
# 6. DB 백업 상태
# =============================================================================
echo "===== 6. DB 백업 ====="
BACKUP_DIR="${BACKUP_DIR:-/var/backups/tradepilot}"
if [[ -d "$BACKUP_DIR" ]]; then
    LATEST=$(ls -t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -1)
    if [[ -n "$LATEST" ]]; then
        AGE_SEC=$(( $(date +%s) - $(stat -c %Y "$LATEST" 2>/dev/null || stat -f %m "$LATEST") ))
        AGE_HR=$((AGE_SEC / 3600))
        if [[ $AGE_HR -le $BACKUP_MAX_AGE_HOURS ]]; then
            ok "최근 백업 ${AGE_HR}시간 전: $(basename "$LATEST")"
        else
            warn "최근 백업이 ${AGE_HR}시간 전 (한도 ${BACKUP_MAX_AGE_HOURS}시간)"
        fi
    else
        warn "백업 파일 없음 (${BACKUP_DIR})"
    fi
else
    warn "백업 디렉토리 없음 (${BACKUP_DIR})"
fi

# =============================================================================
# 결과 요약
# =============================================================================
echo ""
echo "===== 결과 요약 ====="
echo "경고: ${#WARNINGS[@]}건"
echo "실패: ${#ERRORS[@]}건"

if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo ""
    echo "[CRITICAL ERRORS]"
    printf ' - %s\n' "${ERRORS[@]}"
fi
if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    echo ""
    echo "[WARNINGS]"
    printf ' - %s\n' "${WARNINGS[@]}"
fi

exit $EXIT_CODE
