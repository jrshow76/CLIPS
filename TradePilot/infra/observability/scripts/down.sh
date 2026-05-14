#!/usr/bin/env bash
# =============================================================================
# 관측성 스택 정지
# -----------------------------------------------------------------------------
# Usage:
#   bash infra/observability/scripts/down.sh           # 정지만
#   bash infra/observability/scripts/down.sh --purge   # 볼륨까지 삭제(주의)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${PROJECT_ROOT}"

PURGE_FLAG=""
if [[ "${1:-}" == "--purge" ]]; then
  read -r -p "[CONFIRM] 모든 관측성 볼륨(메트릭 30일치, 로그 7일치)을 삭제합니다. 진행? [yes/N] " ans
  if [[ "${ans}" != "yes" ]]; then
    echo "취소됨."
    exit 0
  fi
  PURGE_FLAG="-v"
fi

echo "[INFO] 관측성 스택 정지 중..."
docker compose \
  -f infra/observability/docker-compose.observability.yml \
  down ${PURGE_FLAG}

echo "[OK] 완료."
