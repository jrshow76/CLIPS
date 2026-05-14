#!/usr/bin/env bash
# =============================================================================
# 관측성 스택 기동
# -----------------------------------------------------------------------------
# Usage:
#   bash infra/observability/scripts/up.sh           # 기본
#   bash infra/observability/scripts/up.sh --prod    # prod 오버레이 결합
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${PROJECT_ROOT}"

# 1) .env 검증 (Grafana admin 패스워드 placeholder 차단)
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
fi

if [[ -z "${GRAFANA_ADMIN_PASSWORD:-}" ]]; then
  echo "[ERROR] GRAFANA_ADMIN_PASSWORD 가 비어있습니다. .env 에 설정하세요." >&2
  exit 1
fi
if [[ "${GRAFANA_ADMIN_PASSWORD}" =~ ^(admin|password|change|placeholder|test|tradepilot)$ ]]; then
  echo "[ERROR] GRAFANA_ADMIN_PASSWORD 가 약한 placeholder 값입니다. 무작위 32자 이상으로 교체하세요." >&2
  exit 1
fi

# 2) 외부 네트워크 존재 확인 (메인 스택이 떠 있어야 함)
if ! docker network inspect tradepilot_tp-net >/dev/null 2>&1; then
  echo "[WARN] tradepilot_tp-net 네트워크가 없습니다. 메인 스택을 먼저 기동하세요." >&2
  echo "       docker compose up -d" >&2
  exit 2
fi

# 3) compose 파일 결합
COMPOSE_ARGS=(
  "-f" "infra/observability/docker-compose.observability.yml"
)
if [[ "${1:-}" == "--prod" ]]; then
  COMPOSE_ARGS=(
    "-f" "docker-compose.yml"
    "-f" "docker-compose.prod.yml"
    "-f" "infra/observability/docker-compose.observability.yml"
  )
fi

# 4) 설정 검증
echo "[INFO] 설정 검증 중..."
bash "${SCRIPT_DIR}/seed-alert-rules.sh" || {
  echo "[ERROR] 알림 룰 검증 실패" >&2
  exit 3
}

# 5) 기동
echo "[INFO] 관측성 스택 기동 중..."
docker compose "${COMPOSE_ARGS[@]}" up -d

# 6) 헬스 대기
echo "[INFO] 헬스체크 대기..."
for svc in tp-prometheus tp-alertmanager tp-grafana tp-loki; do
  for _ in $(seq 1 30); do
    status=$(docker inspect -f '{{.State.Health.Status}}' "${svc}" 2>/dev/null || echo "starting")
    if [[ "${status}" == "healthy" ]]; then
      echo "[OK] ${svc} healthy"
      break
    fi
    sleep 2
  done
done

echo
echo "[INFO] 관측성 스택 기동 완료."
echo "  - Grafana   : http://localhost:3000  (사설망 또는 nginx 경유)"
echo "  - Prometheus: http://prometheus:9090 (사설망 한정)"
echo "  - Alertmgr  : http://alertmanager:9093"
echo
echo "Grafana 첫 로그인: admin / \$GRAFANA_ADMIN_PASSWORD"
