#!/usr/bin/env bash
#
# TradePilot 백엔드 스모크 테스트.
#
# 핵심 GET 30개 엔드포인트가 200(또는 401/404 등 사전 정의된 코드)을 반환하는지 확인한다.
# 배포 직후 헬스 체크 + 회귀 가드용.
#
# 실행:
#   BASE_URL=http://localhost:8000 TOKEN=eyJ... bash smoke.sh
#
# 종속성: bash, curl, jq

set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TOKEN="${TOKEN:-}"

# (path, expected_status_code) 쌍.
# 인증 필요 엔드포인트는 401(토큰 없을 때) 또는 200(토큰 있을 때) 모두 허용.
ENDPOINTS=(
  "/healthz|200"
  "/readyz|200"
  "/api/v1/market/index/kospi|200,404"
  "/api/v1/market/index/kosdaq|200,404"
  "/api/v1/stocks/search?q=삼성|200,404"
  "/api/v1/stocks/005930|200,404"
  "/api/v1/chart/005930?interval=D|200,404"
  "/api/v1/indicators?codes=005930&names=rsi&period=14|200,400,404"
  "/api/v1/sectors/rank?period=W|200,404"
  "/api/v1/sectors/flow|200,404"
  "/api/v1/sectors/heatmap|200,404"
  "/api/v1/recommendations?page=1&size=10|200,401,404"
  "/api/v1/recommendations/top|200,401,404"
  "/api/v1/signals?status=ACTIVE&page=1&size=10|200,401,404"
  "/api/v1/strategies?page=1&size=10|200,401,404"
  "/api/v1/orders?page=1&size=10|200,401,404"
  "/api/v1/portfolios|200,401,404"
  "/api/v1/reports/daily-summary|200,401,404"
  "/api/v1/reports/returns?granularity=D|200,401,404"
  "/api/v1/reports/positions|200,401,404"
  "/api/v1/reports/trades?page=1&size=10|200,401,404"
  "/api/v1/reports/strategy-perf|200,401,404"
  "/api/v1/notifications?page=1&size=10|200,401,404"
  "/api/v1/notifications/settings|200,401,404"
  "/api/v1/users/settings|200,401,404"
  "/api/v1/users/limits|200,401,404"
  "/api/v1/users/schedule|200,401,404"
  "/api/v1/auth/me|200,401"
  "/api/v1/ml/predict?code=005930&horizon=1|200,401,404"
  "/api/v1/backtest?page=1&size=10|200,401,404"
)

PASS=0
FAIL=0
FAILED_LINES=()

echo "▶ 스모크 테스트 시작 (BASE_URL=${BASE_URL})"
echo "  대상 엔드포인트: ${#ENDPOINTS[@]}개"
echo

for entry in "${ENDPOINTS[@]}"; do
  path="${entry%%|*}"
  expected="${entry##*|}"

  if [[ -n "${TOKEN}" ]]; then
    code=$(curl -s -o /tmp/smoke-body -w "%{http_code}" \
      -H "Authorization: Bearer ${TOKEN}" \
      "${BASE_URL}${path}")
  else
    code=$(curl -s -o /tmp/smoke-body -w "%{http_code}" \
      "${BASE_URL}${path}")
  fi

  ok=false
  IFS=',' read -ra allowed <<< "${expected}"
  for a in "${allowed[@]}"; do
    if [[ "${code}" == "${a}" ]]; then
      ok=true
      break
    fi
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

echo
echo "──────────────────────────────────────────────"
echo " 통과: ${PASS} / 실패: ${FAIL} / 총 ${#ENDPOINTS[@]}"
echo "──────────────────────────────────────────────"

if [[ ${FAIL} -gt 0 ]]; then
  echo
  echo "실패 목록:"
  for line in "${FAILED_LINES[@]}"; do
    echo "${line}"
  done
  exit 1
fi

exit 0
