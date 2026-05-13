#!/usr/bin/env bash
#
# TradePilot HTTPS 환경 스모크 테스트.
#
# - smoke.sh 의 HTTPS 버전. 프로덕션 nginx 경유 검증용.
# - HSTS, 보안 헤더, HTTP→HTTPS 리디렉션, /metrics 차단을 추가 검증한다.
#
# 실행:
#   BASE_URL=https://tradepilot.example.com TOKEN=eyJ... bash smoke_https.sh
#
# 종속성: bash, curl

set -uo pipefail

BASE_URL="${BASE_URL:-https://tradepilot.example.com}"
TOKEN="${TOKEN:-}"
INSECURE="${INSECURE:-0}"     # 자체서명 인증서 테스트 시 1

CURL_OPTS=(-s -o /tmp/smoke_https-body)
[[ "$INSECURE" == "1" ]] && CURL_OPTS+=(-k)

# (path, expected_status_code) 쌍.
ENDPOINTS=(
    "/healthz|200"
    "/readyz|200"
    "/api/v1/market/index/kospi|200,404"
    "/api/v1/market/index/kosdaq|200,404"
    "/api/v1/stocks/search?q=삼성|200,404"
    "/api/v1/stocks/005930|200,404"
    "/api/v1/chart/005930?interval=D|200,404"
    "/api/v1/sectors/rank?period=W|200,404"
    "/api/v1/recommendations?page=1&size=10|200,401,404"
    "/api/v1/signals?status=ACTIVE&page=1&size=10|200,401,404"
    "/api/v1/orders?page=1&size=10|200,401,404"
    "/api/v1/portfolios|200,401,404"
    "/api/v1/reports/daily-summary|200,401,404"
    "/api/v1/notifications?page=1&size=10|200,401,404"
    "/api/v1/users/settings|200,401,404"
    "/api/v1/auth/me|200,401"
    "/|200"                        # 프론트엔드 메인
    "/_next/static/css/app.css|200,404"   # 자산 (404 허용 - 빌드별 경로 다름)
)

PASS=0
FAIL=0
FAILED_LINES=()

echo "============================================================"
echo " TradePilot HTTPS 스모크 (BASE_URL=${BASE_URL})"
echo "============================================================"
echo

# -----------------------------------------------------------------------------
# 1) 엔드포인트 응답 코드 점검
# -----------------------------------------------------------------------------
echo "[1] 엔드포인트 응답 코드"
for entry in "${ENDPOINTS[@]}"; do
    path="${entry%%|*}"
    expected="${entry##*|}"

    if [[ -n "${TOKEN}" ]]; then
        code=$(curl "${CURL_OPTS[@]}" -w "%{http_code}" \
            -H "Authorization: Bearer ${TOKEN}" \
            "${BASE_URL}${path}")
    else
        code=$(curl "${CURL_OPTS[@]}" -w "%{http_code}" "${BASE_URL}${path}")
    fi

    ok=false
    IFS=',' read -ra allowed <<< "${expected}"
    for a in "${allowed[@]}"; do
        [[ "${code}" == "${a}" ]] && { ok=true; break; }
    done

    if ${ok}; then
        PASS=$((PASS + 1))
        printf "  ✓ %3d  %-60s\n" "${code}" "${path}"
    else
        FAIL=$((FAIL + 1))
        FAILED_LINES+=("  ✗ ${code}  ${path} (expected: ${expected})")
        printf "  ✗ %3d  %-60s (expected: %s)\n" "${code}" "${path}" "${expected}"
    fi
done

# -----------------------------------------------------------------------------
# 2) HTTP → HTTPS 리디렉션
# -----------------------------------------------------------------------------
echo
echo "[2] HTTP → HTTPS 리디렉션"
http_url="http://${BASE_URL#https://}"
redirect_code=$(curl "${CURL_OPTS[@]}" -w "%{http_code}" "${http_url}/")
if [[ "$redirect_code" =~ ^30[1278]$ ]]; then
    PASS=$((PASS + 1))
    echo "  ✓ ${redirect_code}  ${http_url}/ → 리디렉션"
else
    FAIL=$((FAIL + 1))
    FAILED_LINES+=("  ✗ ${redirect_code}  HTTP→HTTPS 리디렉션 실패")
    echo "  ✗ ${redirect_code}  HTTP→HTTPS 리디렉션 실패"
fi

# -----------------------------------------------------------------------------
# 3) 보안 헤더 검증
# -----------------------------------------------------------------------------
echo
echo "[3] 보안 헤더"
headers=$(curl "${CURL_OPTS[@]}" -I "${BASE_URL}/" 2>/dev/null || curl -sI ${INSECURE:+-k} "${BASE_URL}/")

check_hdr() {
    local name="$1" pattern="$2"
    if echo "$headers" | grep -i "^${name}:" | grep -qE "$pattern"; then
        PASS=$((PASS + 1))
        printf "  ✓ %-40s\n" "${name}"
    else
        FAIL=$((FAIL + 1))
        FAILED_LINES+=("  ✗ Header ${name} 누락/부적합")
        printf "  ✗ %-40s (누락/부적합)\n" "${name}"
    fi
}

check_hdr "Strict-Transport-Security" "max-age=[0-9]+"
check_hdr "X-Frame-Options"            "DENY|SAMEORIGIN"
check_hdr "X-Content-Type-Options"     "nosniff"
check_hdr "Referrer-Policy"            "."
check_hdr "Permissions-Policy"         "."

# Server 헤더 비노출 확인
if echo "$headers" | grep -i "^Server:" | grep -qiE "nginx/[0-9]"; then
    FAIL=$((FAIL + 1))
    FAILED_LINES+=("  ✗ Server 헤더에 버전 노출 (server_tokens off 확인)")
    echo "  ✗ Server 헤더 버전 노출"
else
    PASS=$((PASS + 1))
    echo "  ✓ Server 헤더 버전 미노출"
fi

# -----------------------------------------------------------------------------
# 4) /metrics 외부 차단 확인
# -----------------------------------------------------------------------------
echo
echo "[4] /metrics 외부 차단"
metrics_code=$(curl "${CURL_OPTS[@]}" -w "%{http_code}" "${BASE_URL}/metrics")
if [[ "$metrics_code" == "403" || "$metrics_code" == "404" ]]; then
    PASS=$((PASS + 1))
    echo "  ✓ ${metrics_code}  /metrics 외부 접근 차단됨"
else
    FAIL=$((FAIL + 1))
    FAILED_LINES+=("  ✗ ${metrics_code}  /metrics 가 외부에 노출됨")
    echo "  ✗ ${metrics_code}  /metrics 가 외부에 노출됨!"
fi

# -----------------------------------------------------------------------------
# 결과
# -----------------------------------------------------------------------------
echo
echo "============================================================"
echo " 통과: ${PASS} / 실패: ${FAIL}"
echo "============================================================"

if [[ ${FAIL} -gt 0 ]]; then
    echo
    echo "실패 목록:"
    for line in "${FAILED_LINES[@]}"; do
        echo "${line}"
    done
    exit 1
fi

exit 0
