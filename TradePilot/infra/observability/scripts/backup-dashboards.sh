#!/usr/bin/env bash
# =============================================================================
# Grafana 대시보드 백업
# -----------------------------------------------------------------------------
# Grafana 가 실행 중인 상태에서 모든 대시보드 JSON 을 export 한다.
# - 인증: API key 또는 admin basic
# - 출력: infra/observability/grafana/dashboards-backup/YYYYMMDD/*.json
#
# Usage:
#   GRAFANA_API_KEY=glsa_... bash infra/observability/scripts/backup-dashboards.sh
#   # 또는
#   GRAFANA_ADMIN_USER=admin GRAFANA_ADMIN_PASSWORD=... bash .../backup-dashboards.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"

if [[ -z "${GRAFANA_API_KEY:-}" && -z "${GRAFANA_ADMIN_PASSWORD:-}" ]]; then
  echo "[ERROR] GRAFANA_API_KEY 또는 GRAFANA_ADMIN_PASSWORD 가 필요합니다." >&2
  exit 1
fi

AUTH_HEADER=()
if [[ -n "${GRAFANA_API_KEY:-}" ]]; then
  AUTH_HEADER=("-H" "Authorization: Bearer ${GRAFANA_API_KEY}")
else
  CURL_USER="${GRAFANA_ADMIN_USER:-admin}:${GRAFANA_ADMIN_PASSWORD}"
fi

OUT_DIR="${ROOT}/grafana/dashboards-backup/$(date +%Y%m%d)"
mkdir -p "${OUT_DIR}"

echo "[INFO] 대시보드 목록 조회..."
if [[ -n "${GRAFANA_API_KEY:-}" ]]; then
  LIST=$(curl -fsS "${AUTH_HEADER[@]}" "${GRAFANA_URL}/api/search?type=dash-db")
else
  LIST=$(curl -fsS -u "${CURL_USER}" "${GRAFANA_URL}/api/search?type=dash-db")
fi

count=0
echo "${LIST}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for d in data:
    print(d['uid'])
" | while read -r UID; do
  echo "  - ${UID}"
  if [[ -n "${GRAFANA_API_KEY:-}" ]]; then
    curl -fsS "${AUTH_HEADER[@]}" "${GRAFANA_URL}/api/dashboards/uid/${UID}" \
      > "${OUT_DIR}/${UID}.json"
  else
    curl -fsS -u "${CURL_USER}" "${GRAFANA_URL}/api/dashboards/uid/${UID}" \
      > "${OUT_DIR}/${UID}.json"
  fi
  count=$((count + 1))
done

echo
echo "[OK] ${OUT_DIR} 에 ${count} 개 대시보드 백업 완료."
