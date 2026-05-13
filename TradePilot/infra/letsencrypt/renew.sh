#!/usr/bin/env bash
# =============================================================================
# Let's Encrypt 자동 갱신 스크립트 (TradePilot)
# -----------------------------------------------------------------------------
# - certbot renew 는 만료 30일 이내 인증서만 실제 갱신 → cron으로 매일 돌려도 안전
# - 갱신 시에만 nginx 재로드 (--deploy-hook 사용)
# - 표준 출력은 cron MAIL 로 전달, 에러는 로그파일 별도 보관
#
# cron 등록 예 (root):
#   0 3 * * * /home/user/CLIPS/TradePilot/infra/letsencrypt/renew.sh >> /var/log/letsencrypt-renew.log 2>&1
#
# systemd timer 등록 예:
#   /etc/systemd/system/letsencrypt-renew.service
#   /etc/systemd/system/letsencrypt-renew.timer  (OnCalendar=*-*-* 03:00:00)
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
COMPOSE_PROD="${PROJECT_ROOT}/docker-compose.prod.yml"

dc() {
    docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_PROD}" "$@"
}

ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] Let's Encrypt 갱신 점검 시작"

# -----------------------------------------------------------------------------
# 1) certbot renew (Dry run으로 사전 검증) - 옵션
# -----------------------------------------------------------------------------
if [[ "${DRY_RUN_FIRST:-0}" == "1" ]]; then
    echo "[$(ts)] dry-run 사전 검증..."
    dc run --rm --entrypoint "certbot renew --dry-run" certbot
fi

# -----------------------------------------------------------------------------
# 2) 실제 갱신 수행
#    - --deploy-hook : 갱신 성공 시에만 nginx 재로드 (불필요한 재로드 방지)
# -----------------------------------------------------------------------------
echo "[$(ts)] 갱신 수행..."
dc run --rm --entrypoint "\
    certbot renew \
        --webroot -w /var/www/certbot \
        --deploy-hook 'touch /var/www/certbot/.renewed'" certbot

# -----------------------------------------------------------------------------
# 3) 갱신 마커 확인 → nginx 재로드
# -----------------------------------------------------------------------------
RENEWED_MARKER="${PROJECT_ROOT}/infra/letsencrypt/data/www/.renewed"
if [[ -f "${RENEWED_MARKER}" ]]; then
    echo "[$(ts)] 인증서 갱신 감지 → nginx 무중단 재로드"
    dc exec -T nginx nginx -t
    dc exec -T nginx nginx -s reload
    rm -f "${RENEWED_MARKER}"
else
    # 컨테이너 내부 마커는 docker 볼륨이라 host에 안 보일 수 있음 → 보수적으로 항상 nginx -t 만 검증
    echo "[$(ts)] 호스트 마커 없음 (volume 사용 시 정상). 컨테이너에서 마커 확인."
    if dc exec -T nginx test -f /var/www/certbot/.renewed 2>/dev/null; then
        echo "[$(ts)] 컨테이너 내 마커 발견 → nginx 재로드"
        dc exec -T nginx nginx -t
        dc exec -T nginx nginx -s reload
        dc exec -T nginx rm -f /var/www/certbot/.renewed
    else
        echo "[$(ts)] 갱신 대상 없음 (만료 30일 이상 남음)"
    fi
fi

echo "[$(ts)] 갱신 점검 종료"
