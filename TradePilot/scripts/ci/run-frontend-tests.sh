#!/usr/bin/env bash
# run-frontend-tests.sh - lint / type-check / build 를 일관되게 실행.
#
# 사용:
#   ./run-frontend-tests.sh             # lint + type-check + build
#   ./run-frontend-tests.sh lint
#   ./run-frontend-tests.sh type
#   ./run-frontend-tests.sh build

set -euo pipefail

scope="${1:-all}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)/frontend"
cd "${FRONT_DIR}"

export NEXT_PUBLIC_USE_MOCK="${NEXT_PUBLIC_USE_MOCK:-true}"
export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:8000/api/v1}"
export NEXT_PUBLIC_WS_BASE_URL="${NEXT_PUBLIC_WS_BASE_URL:-ws://localhost:8000/ws}"
export NEXT_PUBLIC_APP_ENV="${NEXT_PUBLIC_APP_ENV:-ci}"
export NEXT_TELEMETRY_DISABLED="1"

if [ ! -d node_modules ]; then
  echo "[frontend] node_modules 없음 -> npm ci"
  npm ci --no-audit --no-fund
fi

case "${scope}" in
  lint)
    npm run lint
    ;;
  type)
    npx tsc --noEmit
    ;;
  build)
    npm run build
    ;;
  all)
    npm run lint
    npx tsc --noEmit
    npm run build
    ;;
  *)
    echo "알 수 없는 scope: ${scope} (lint|type|build|all)" >&2
    exit 2
    ;;
esac

echo "[frontend] 완료 (scope=${scope})"
