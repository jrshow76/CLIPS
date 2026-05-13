#!/usr/bin/env bash
# =============================================================================
# nginx 무중단 재로드
# -----------------------------------------------------------------------------
# - nginx -t 로 설정 검증 후 nginx -s reload
# - 검증 실패 시 재로드하지 않고 exit 1
# - 기존 worker는 처리 중인 요청을 마치고 graceful 종료
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "${PROJECT_ROOT}"

COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)

ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] 1) nginx 설정 문법 검증 (nginx -t)..."
if ! docker compose "${COMPOSE_FILES[@]}" exec -T nginx nginx -t; then
    echo "[$(ts)] ERROR: nginx 설정 검증 실패. 재로드를 중단합니다." >&2
    exit 1
fi

echo "[$(ts)] 2) nginx 무중단 재로드 (nginx -s reload)..."
docker compose "${COMPOSE_FILES[@]}" exec -T nginx nginx -s reload

echo "[$(ts)] 3) worker 프로세스 확인..."
docker compose "${COMPOSE_FILES[@]}" exec -T nginx sh -c 'ps -ef | grep "[n]ginx"' || true

echo "[$(ts)] 4) 헬스 체크..."
sleep 1
if curl -sk -o /dev/null -w "  status=%{http_code}  time=%{time_total}s\n" https://localhost/healthz; then
    echo "[$(ts)] 재로드 완료"
else
    echo "[$(ts)] WARN: 헬스 응답을 받지 못했습니다. 로그 확인 필요." >&2
fi
