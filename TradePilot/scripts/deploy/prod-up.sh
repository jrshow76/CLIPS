#!/usr/bin/env bash
# =============================================================================
# TradePilot 프로덕션 기동
# -----------------------------------------------------------------------------
# 사용법:
#   bash scripts/deploy/prod-up.sh           # 전체 기동
#   bash scripts/deploy/prod-up.sh --pull    # 이미지 pull 후 기동
#   bash scripts/deploy/prod-up.sh --build   # 이미지 빌드 후 기동
#   bash scripts/deploy/prod-up.sh nginx     # 특정 서비스만 기동
#
# 사전조건:
#   - .env 파일 존재
#   - infra/nginx/ssl/dhparam.pem 생성 완료
#   - Let's Encrypt 인증서 발급 완료 (init-letsencrypt.sh)
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "${PROJECT_ROOT}"

COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)

# ----- 사전 검증 -----
if [[ ! -f .env ]]; then
    echo "ERROR: .env 파일이 없습니다. .env.example 을 복사하여 생성하세요." >&2
    exit 1
fi

if [[ ! -f infra/nginx/ssl/dhparam.pem ]]; then
    echo "ERROR: infra/nginx/ssl/dhparam.pem 이 없습니다." >&2
    echo "       infra/nginx/dhparam.pem.note.md 참고하여 생성하세요." >&2
    exit 1
fi

# ----- 옵션 파싱 -----
PULL=false
BUILD=false
SERVICES=()
for arg in "$@"; do
    case "$arg" in
        --pull)  PULL=true ;;
        --build) BUILD=true ;;
        *)       SERVICES+=("$arg") ;;
    esac
done

# ----- 실행 -----
if [[ "$PULL" == "true" ]]; then
    echo "[1/3] 이미지 pull..."
    docker compose "${COMPOSE_FILES[@]}" pull "${SERVICES[@]}"
fi

if [[ "$BUILD" == "true" ]]; then
    echo "[2/3] 이미지 빌드..."
    docker compose "${COMPOSE_FILES[@]}" build "${SERVICES[@]}"
fi

echo "[3/3] 기동..."
docker compose "${COMPOSE_FILES[@]}" up -d "${SERVICES[@]}"

echo
echo "============================================================"
echo " 기동 완료. 상태 확인:"
echo "============================================================"
docker compose "${COMPOSE_FILES[@]}" ps

echo
echo "헬스 체크:"
sleep 3
curl -sk https://localhost/healthz | head -5 || echo "  (HTTPS 헬스 응답 없음 - 인증서 발급 여부 확인)"
