#!/usr/bin/env bash
# TradePilot 초기 시장 데이터 적재 (docker exec 래퍼).
#
# 컨테이너 가정:
#   - backend 서비스 명: tradepilot-backend (docker-compose.yml 기준)
#   - 컨테이너 내부 워킹디렉토리: /app
#   - 백엔드 패키지: /app/app
#
# 사용법:
#   bash scripts/ingest_initial_data.sh
#   bash scripts/ingest_initial_data.sh --start 2021-01-01
#   bash scripts/ingest_initial_data.sh --skip-backfill
#
# 주의:
#   - 5년 전 종목 백필은 수십분~수 시간 소요됩니다.
#   - 운영 환경 실행 전 반드시 staging에서 시간 측정.

set -euo pipefail

CONTAINER_NAME="${TRADEPILOT_BACKEND_CONTAINER:-tradepilot-backend}"
SCRIPT_PATH_IN_CONTAINER="/app/scripts/ingest_initial_data.py"

# 컨테이너 가용성 체크
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
    echo "[ERROR] 컨테이너 '${CONTAINER_NAME}' 가 실행 중이 아닙니다." >&2
    echo "         docker compose up -d 를 먼저 실행하세요." >&2
    exit 1
fi

echo "[INFO] 초기 적재 실행: 컨테이너=${CONTAINER_NAME}"
echo "[INFO] 인자: $*"

docker exec -i "${CONTAINER_NAME}" \
    python "${SCRIPT_PATH_IN_CONTAINER}" "$@"

echo "[OK] 초기 적재 완료"
