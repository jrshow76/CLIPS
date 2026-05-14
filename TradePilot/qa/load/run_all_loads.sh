#!/usr/bin/env bash
#
# TradePilot 부하 테스트 일괄 실행 스크립트.
#
# - qa/load/k6_*.js 시나리오를 순차 실행.
# - 결과 JSON을 reports/ 디렉토리에 저장하고, 실행 환경 메타데이터 함께 기록.
# - 한 시나리오라도 threshold 위반이면 다음 시나리오는 계속 진행하고 종료 코드 1.
#
# 사용:
#   BASE_URL=http://localhost:8000 TOKEN=eyJ... \
#   bash qa/load/run_all_loads.sh
#
# 옵션:
#   SKIP_WS=1                  WS 시나리오 제외
#   SKIP_BACKTEST=1            백테스트 시나리오 제외 (오래 걸림)
#   SCENARIOS="orders signals" 지정 시나리오만 실행
#
# 종속성: k6 (>=0.50), bash, jq

set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TOKEN="${TOKEN:-}"
SKIP_WS="${SKIP_WS:-0}"
SKIP_BACKTEST="${SKIP_BACKTEST:-1}"  # 기본 제외 (오래 걸림)
SCENARIOS="${SCENARIOS:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPORTS_DIR="${REPO_ROOT}/qa/load/reports"
mkdir -p "${REPORTS_DIR}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
META_FILE="${REPORTS_DIR}/run_${TIMESTAMP}_meta.json"

# 시나리오 정의: name|script|description
ALL=(
  "orders|k6_orders_burst.js|주문 API 100 RPS / 5분"
  "signals|k6_signals_burst.js|시그널 조회 200 RPS / 5분"
  "ws|k6_ws_burst.js|WebSocket 1,000 동시 연결 / 5분"
  "mixed|k6_api_mixed.js|혼합 워크로드 50VU / 10분"
  "backtest|k6_backtest_concurrent.js|백테스트 동시 10건"
)

# 필터링
RUN_LIST=()
for entry in "${ALL[@]}"; do
  IFS='|' read -r name script desc <<< "${entry}"
  # SKIP 플래그
  [[ "${name}" == "ws" && "${SKIP_WS}" == "1" ]] && continue
  [[ "${name}" == "backtest" && "${SKIP_BACKTEST}" == "1" ]] && continue
  # SCENARIOS 명시 시 필터
  if [[ -n "${SCENARIOS}" ]]; then
    [[ " ${SCENARIOS} " =~ \ ${name}\  ]] || continue
  fi
  RUN_LIST+=("${entry}")
done

# 메타데이터 수집
cat > "${META_FILE}" <<EOF
{
  "timestamp": "${TIMESTAMP}",
  "base_url": "${BASE_URL}",
  "host": "$(hostname)",
  "kernel": "$(uname -r)",
  "cpu_count": $(nproc 2>/dev/null || echo 0),
  "k6_version": "$(k6 version 2>/dev/null | head -1 || echo unknown)",
  "scenarios": [$(printf '"%s",' "${RUN_LIST[@]/#/}" | sed 's/,$//')]
}
EOF

echo "============================================================"
echo " TradePilot 부하 테스트 일괄 실행"
echo "============================================================"
echo " BASE_URL : ${BASE_URL}"
echo " 실행 수  : ${#RUN_LIST[@]}"
echo " 메타     : ${META_FILE}"
echo

if ! command -v k6 >/dev/null 2>&1; then
  echo "ERROR: k6 가 설치되어 있지 않다. https://k6.io/docs/get-started/installation/"
  exit 2
fi

FAIL_COUNT=0
for entry in "${RUN_LIST[@]}"; do
  IFS='|' read -r name script desc <<< "${entry}"
  SCRIPT_PATH="${SCRIPT_DIR}/${script}"
  OUT_JSON="${REPORTS_DIR}/${TIMESTAMP}_${name}.json"
  OUT_LOG="${REPORTS_DIR}/${TIMESTAMP}_${name}.log"

  echo "------------------------------------------------------------"
  echo "▶ [${name}] ${desc}"
  echo "  스크립트: ${script}"
  echo "  결과 JSON: ${OUT_JSON}"
  echo

  if [[ ! -f "${SCRIPT_PATH}" ]]; then
    echo "  ✗ 스크립트 누락: ${SCRIPT_PATH}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    continue
  fi

  # k6 실행: summary export + 별도 로그
  BASE_URL="${BASE_URL}" TOKEN="${TOKEN}" \
    k6 run \
      --summary-export="${OUT_JSON}" \
      "${SCRIPT_PATH}" 2>&1 | tee "${OUT_LOG}"
  rc=${PIPESTATUS[0]}

  if [[ ${rc} -ne 0 ]]; then
    echo "  ✗ [${name}] threshold 위반 또는 오류 (exit=${rc})"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  else
    echo "  ✓ [${name}] 성공"
  fi
  echo
done

echo "============================================================"
echo " 완료: 총 ${#RUN_LIST[@]} / 실패 ${FAIL_COUNT}"
echo " 결과 디렉토리: ${REPORTS_DIR}"
echo "============================================================"

# 분석 자동 실행 (가능 시)
if command -v python3 >/dev/null 2>&1 && [[ -f "${SCRIPT_DIR}/analyze_results.py" ]]; then
  echo
  echo "▶ analyze_results.py 실행"
  python3 "${SCRIPT_DIR}/analyze_results.py" \
    --reports-dir "${REPORTS_DIR}" \
    --timestamp "${TIMESTAMP}" \
    --out "${REPORTS_DIR}/${TIMESTAMP}_analysis.md" || true
fi

if [[ ${FAIL_COUNT} -gt 0 ]]; then
  exit 1
fi
exit 0
