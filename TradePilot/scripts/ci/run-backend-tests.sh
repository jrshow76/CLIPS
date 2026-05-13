#!/usr/bin/env bash
# run-backend-tests.sh - CI 와 로컬에서 동일하게 백엔드 테스트를 수행하기 위한 진입점.
#
# 사용:
#   ./run-backend-tests.sh           # unit + integration + qa 전체
#   ./run-backend-tests.sh unit      # 단위만
#   ./run-backend-tests.sh integration
#   ./run-backend-tests.sh qa
#   ./run-backend-tests.sh lint      # ruff + black 만
#
# 환경변수 (없으면 로컬 docker-compose 기본값을 가정):
#   DATABASE_URL  postgresql+asyncpg://...
#   REDIS_URL     redis://...
#   JWT_SECRET, AES_KEY  (테스트용 mock)

set -euo pipefail

scope="${1:-all}"

# 스크립트 위치 기준 backend 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)/backend"
cd "${BACKEND_DIR}"

# 로컬 기본값 (CI 에서는 워크플로우 env 가 우선 적용됨)
export APP_ENV="${APP_ENV:-test}"
export LOG_LEVEL="${LOG_LEVEL:-WARNING}"
export JWT_SECRET="${JWT_SECRET:-test-secret-test-secret-test-secret-test}"
export AES_KEY="${AES_KEY:-test-aes-key-32-byte-test-key-12}"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://tradepilot:tradepilot@localhost:5432/tradepilot_test}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export REDIS_BROKER_URL="${REDIS_BROKER_URL:-redis://localhost:6379/1}"
export REDIS_RESULT_URL="${REDIS_RESULT_URL:-redis://localhost:6379/2}"
export CREON_GATEWAY_URL="${CREON_GATEWAY_URL:-http://localhost:9000}"
export CREON_GATEWAY_API_KEY="${CREON_GATEWAY_API_KEY:-test-gateway-key}"

mkdir -p reports

run_lint() {
  echo "[backend] ruff check"
  ruff check app tests
  echo "[backend] black --check"
  black --check app tests
}

run_unit() {
  echo "[backend] pytest unit"
  pytest tests/unit -m "not integration and not slow" \
    --cov=app --cov-report=xml:coverage-unit.xml \
    --junitxml=reports/junit-unit.xml
}

run_integration() {
  echo "[backend] pytest integration"
  pytest tests/integration \
    --cov=app --cov-append --cov-report=xml:coverage-integration.xml \
    --junitxml=reports/junit-integration.xml
}

run_qa() {
  echo "[backend] pytest qa"
  pytest tests/qa --junitxml=reports/junit-qa.xml
}

case "${scope}" in
  lint)
    run_lint
    ;;
  unit)
    run_unit
    ;;
  integration)
    run_integration
    ;;
  qa)
    run_qa
    ;;
  all)
    run_lint
    run_unit
    run_integration
    run_qa
    ;;
  *)
    echo "알 수 없는 scope: ${scope} (lint|unit|integration|qa|all)" >&2
    exit 2
    ;;
esac

echo "[backend] 완료 (scope=${scope})"
