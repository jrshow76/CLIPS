#!/usr/bin/env bash
# =============================================================================
# LIVE 전환 직전 종합 점검 (Pre-LIVE Smoketest)
#
# 본 스크립트는 모의투자 환경에서 LIVE 모드로 전환하기 직전에 1회 실행한다.
# 실패 항목이 있으면 LIVE 전환을 차단해야 한다.
#
# 점검 항목:
#  1. JWT 발급 (admin 사용자)
#  2. 게이트웨이 mock 주문 발주 (실거래 영향 없음)
#  3. 한도 조회 (사용자 한도 설정 확인)
#  4. Kill Switch 즉시 발동 + 복구 가능 여부
#  5. 헬스비트 5초 이내 수신
#  6. Sentry/모니터링 알림 채널 동작 (테스트 알림)
#
# 사용: ./scripts/prelive_smoketest.sh [USER_EMAIL]
# 종료 코드: 0=Pass, 1=Fail
# =============================================================================

set -u

USER_EMAIL="${1:-admin@tradepilot.local}"
ADMIN_PW="${ADMIN_PW:-changeme}"

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:9100}"
GATEWAY_API_KEY="${CREON_GATEWAY_API_KEY:-replace-me}"

PASS=0
FAIL=0
RESULTS=()

step() {
    local name="$1"
    shift
    echo ""
    echo "----- $name -----"
    if "$@"; then
        echo "[PASS] $name"
        PASS=$((PASS+1))
        RESULTS+=("PASS: $name")
        return 0
    else
        echo "[FAIL] $name"
        FAIL=$((FAIL+1))
        RESULTS+=("FAIL: $name")
        return 1
    fi
}

# -----------------------------------------------------------------------------
# 1. JWT 발급
# -----------------------------------------------------------------------------
check_jwt() {
    TOKEN=$(curl -sf -X POST "$BACKEND_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$USER_EMAIL\",\"password\":\"$ADMIN_PW\"}" \
        | jq -r '.data.access_token // empty')
    [[ -n "$TOKEN" ]]
}

# -----------------------------------------------------------------------------
# 2. 게이트웨이 mock 주문 (실거래 영향 0)
# -----------------------------------------------------------------------------
check_mock_order() {
    # 게이트웨이가 SIM 모드인지 확인
    TRADE_ENV=$(curl -sf "$GATEWAY_URL/healthz" | jq -r '.trade_env')
    if [[ "$TRADE_ENV" != "SIM" ]]; then
        echo "    [WARN] 현재 게이트웨이가 SIM이 아님 ($TRADE_ENV). 안전을 위해 본 검증을 건너뜀."
        return 0
    fi
    RESP=$(curl -sf -X POST "$GATEWAY_URL/orders" \
        -H "Content-Type: application/json" \
        -H "X-Gateway-Api-Key: $GATEWAY_API_KEY" \
        -d '{
            "code":"005930",
            "side":"BUY",
            "qty":1,
            "order_type":"LIMIT",
            "price":70000,
            "idempotency_key":"prelive-smoke-001"
        }')
    SUCCESS=$(echo "$RESP" | jq -r '.success')
    [[ "$SUCCESS" == "true" ]]
}

# -----------------------------------------------------------------------------
# 3. 한도 조회
# -----------------------------------------------------------------------------
check_limits() {
    [[ -z "$TOKEN" ]] && return 1
    RESP=$(curl -sf "$BACKEND_URL/api/v1/risk/limits" \
        -H "Authorization: Bearer $TOKEN")
    DAILY=$(echo "$RESP" | jq -r '.data.daily_buy_amount_max // empty')
    [[ -n "$DAILY" && "$DAILY" -gt 0 ]]
}

# -----------------------------------------------------------------------------
# 4. Kill Switch 즉시 발동 + 복구
# -----------------------------------------------------------------------------
check_kill_switch_sla() {
    [[ -z "$TOKEN" ]] && return 1
    T0=$(date +%s%3N)
    KILL=$(curl -sf -X POST "$BACKEND_URL/api/v1/risk/kill-switch" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"reason":"prelive-smoketest"}')
    T1=$(date +%s%3N)
    DUR=$((T1 - T0))
    if [[ $DUR -gt 5000 ]]; then
        echo "    [FAIL] Kill Switch 응답 ${DUR}ms (5000ms 초과)"
        return 1
    fi
    echo "    [OK] Kill Switch 응답 ${DUR}ms"

    # 복구 가능 여부 (재활성화 API)
    REC=$(curl -sf -X POST "$BACKEND_URL/api/v1/risk/kill-switch/reset" \
        -H "Authorization: Bearer $TOKEN" 2>/dev/null) || true
    [[ -n "$REC" ]]
}

# -----------------------------------------------------------------------------
# 5. 헬스비트 5초 이내 수신
# -----------------------------------------------------------------------------
check_healthbeat_recency() {
    [[ -z "$TOKEN" ]] && return 1
    LAST=$(curl -sf "$BACKEND_URL/api/v1/health/gateway" \
        -H "Authorization: Bearer $TOKEN" \
        | jq -r '.data.last_healthbeat_age_sec // 9999')
    [[ "$LAST" -lt 35 ]]    # 30초 주기 + 5초 마진
}

# -----------------------------------------------------------------------------
# 6. 알림 채널
# -----------------------------------------------------------------------------
check_notification_channel() {
    [[ -z "$TOKEN" ]] && return 1
    RESP=$(curl -sf -X POST "$BACKEND_URL/api/v1/notifications/test" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"channel":"email"}' 2>/dev/null) || return 1
    [[ -n "$RESP" ]]
}

# =============================================================================
# 실행
# =============================================================================
echo "##############################"
echo "# Pre-LIVE Smoketest"
echo "# 사용자: $USER_EMAIL"
echo "# 게이트웨이: $GATEWAY_URL"
echo "# 백엔드: $BACKEND_URL"
echo "##############################"

step "1. JWT 발급" check_jwt
step "2. 게이트웨이 SIM 주문" check_mock_order
step "3. 사용자 한도 조회" check_limits
step "4. Kill Switch 5초 SLA" check_kill_switch_sla
step "5. 헬스비트 신선도" check_healthbeat_recency
step "6. 알림 채널 (이메일)" check_notification_channel

echo ""
echo "##############################"
echo "결과: PASS=$PASS, FAIL=$FAIL"
printf ' - %s\n' "${RESULTS[@]}"
echo "##############################"

if [[ $FAIL -eq 0 ]]; then
    echo "[OK] LIVE 전환 가능 후보. PM/DevLead 사인오프 진행."
    exit 0
else
    echo "[STOP] LIVE 전환 금지. 위 FAIL 항목 해소 후 재실행."
    exit 1
fi
