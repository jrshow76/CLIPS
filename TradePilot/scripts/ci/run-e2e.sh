#!/usr/bin/env bash
# run-e2e.sh - 프런트엔드 mock 모드 + Playwright 시나리오를 로컬/CI 동일하게 실행.
#
# 사용:
#   ./run-e2e.sh                       # 전체 project
#   ./run-e2e.sh chromium              # 특정 project
#   ./run-e2e.sh mobile-chromium
#
# 동작:
#   1) frontend 빌드 + start (port 3000) 백그라운드 기동
#   2) 헬스 대기
#   3) playwright test
#   4) 종료 시 frontend 프로세스 정리

set -euo pipefail

project="${1:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONT_DIR="${ROOT_DIR}/frontend"
E2E_DIR="${ROOT_DIR}/qa/e2e"

export NEXT_PUBLIC_USE_MOCK="true"
export NEXT_PUBLIC_API_BASE_URL="http://localhost:8000/api/v1"
export NEXT_PUBLIC_WS_BASE_URL="ws://localhost:8000/ws"
export NEXT_PUBLIC_APP_ENV="ci"
export NEXT_TELEMETRY_DISABLED="1"
export E2E_BASE_URL="http://localhost:3000"
export CI="${CI:-true}"

# ---- 1) frontend 준비 ----
cd "${FRONT_DIR}"
if [ ! -d node_modules ]; then
  npm ci --no-audit --no-fund
fi
npm run build

nohup npm run start > /tmp/frontend.log 2>&1 &
FRONT_PID=$!
echo "${FRONT_PID}" > /tmp/frontend.pid
echo "[e2e] frontend 기동 PID=${FRONT_PID}"

cleanup() {
  if [ -n "${FRONT_PID:-}" ] && kill -0 "${FRONT_PID}" 2>/dev/null; then
    kill "${FRONT_PID}" 2>/dev/null || true
  fi
  echo "[e2e] frontend 정리 완료"
}
trap cleanup EXIT

# ---- 2) 헬스 대기 ----
bash "${SCRIPT_DIR}/wait-for.sh" localhost 3000 90

# ---- 3) E2E 의존성 + 실행 ----
cd "${E2E_DIR}"
if [ ! -d node_modules ]; then
  if [ -f package-lock.json ]; then
    npm ci --no-audit --no-fund
  else
    npm install --no-audit --no-fund
  fi
fi
npx playwright install --with-deps

if [ -n "${project}" ]; then
  npx playwright test --project="${project}" --reporter=list,html,junit
else
  npx playwright test --reporter=list,html,junit
fi
