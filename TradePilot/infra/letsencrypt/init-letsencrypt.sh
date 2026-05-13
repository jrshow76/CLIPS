#!/usr/bin/env bash
# =============================================================================
# Let's Encrypt 최초 발급 스크립트 (TradePilot)
# -----------------------------------------------------------------------------
# 절차:
#   1) 더미 자체서명 인증서 생성 (nginx 부팅용 임시)
#   2) nginx 기동 (HTTP 80 + HTTPS 443 둘 다 listen 필요)
#   3) certbot 스테이징 환경에서 발급 시도 (Rate Limit 안전)
#   4) 스테이징 성공 시 더미 인증서 삭제
#   5) certbot 프로덕션 환경에서 실제 발급
#   6) nginx 재로드
#
# 사용법:
#   sudo DOMAIN=tradepilot.example.com EMAIL=admin@example.com \
#        bash infra/letsencrypt/init-letsencrypt.sh
#
# 환경변수:
#   DOMAIN     - 발급 대상 도메인 (필수, 콤마로 멀티 도메인 가능)
#   EMAIL      - Let's Encrypt 만료 알림 이메일 (필수)
#   STAGING    - 1이면 스테이징만 발급하고 종료 (테스트용, 기본 0)
#   RSA_KEY_SIZE - RSA 키 크기 (기본 4096)
# =============================================================================

set -euo pipefail

# ----- 설정 -----
DOMAIN="${DOMAIN:?DOMAIN 환경변수가 필요합니다 (예: tradepilot.example.com)}"
EMAIL="${EMAIL:?EMAIL 환경변수가 필요합니다}"
STAGING="${STAGING:-0}"
RSA_KEY_SIZE="${RSA_KEY_SIZE:-4096}"

# 프로젝트 루트 (스크립트 위치 기준)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
COMPOSE_PROD="${PROJECT_ROOT}/docker-compose.prod.yml"

DATA_PATH="./certbot"            # docker volume이 아닌 호스트 경로 사용 시
PRIMARY_DOMAIN="${DOMAIN%%,*}"   # 첫 번째 도메인 (디렉토리명용)

DOMAIN_ARGS=""
IFS=',' read -ra DOMAINS <<< "$DOMAIN"
for d in "${DOMAINS[@]}"; do
    DOMAIN_ARGS="${DOMAIN_ARGS} -d ${d}"
done

# docker compose 명령 wrapper
dc() {
    docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_PROD}" "$@"
}

echo "============================================================"
echo " TradePilot Let's Encrypt 최초 발급"
echo "============================================================"
echo "  도메인       : ${DOMAIN}"
echo "  이메일       : ${EMAIL}"
echo "  스테이징만   : ${STAGING}"
echo "  RSA 키 크기  : ${RSA_KEY_SIZE}"
echo "============================================================"
echo

# -----------------------------------------------------------------------------
# Pre-flight: DNS A 레코드 확인 (단순 경고)
# -----------------------------------------------------------------------------
echo "[Pre-flight] DNS 확인..."
for d in "${DOMAINS[@]}"; do
    resolved=$(getent hosts "$d" | awk '{print $1}' | head -1 || true)
    if [[ -z "$resolved" ]]; then
        echo "  경고: ${d} 가 DNS에서 해석되지 않습니다. A 레코드를 먼저 등록하세요."
    else
        echo "  ${d} → ${resolved}"
    fi
done
echo

# -----------------------------------------------------------------------------
# 1) 더미 자체서명 인증서 생성 (nginx가 443 listen 가능하도록)
# -----------------------------------------------------------------------------
echo "[1/6] 더미 자체서명 인증서 생성 (nginx 부팅용)..."
dc run --rm --entrypoint "\
    sh -c 'mkdir -p /etc/letsencrypt/live/${PRIMARY_DOMAIN} && \
           openssl req -x509 -nodes -newkey rsa:${RSA_KEY_SIZE} -days 1 \
             -keyout /etc/letsencrypt/live/${PRIMARY_DOMAIN}/privkey.pem \
             -out    /etc/letsencrypt/live/${PRIMARY_DOMAIN}/fullchain.pem \
             -subj   /CN=${PRIMARY_DOMAIN} && \
           cp /etc/letsencrypt/live/${PRIMARY_DOMAIN}/fullchain.pem \
              /etc/letsencrypt/live/${PRIMARY_DOMAIN}/chain.pem'" certbot

# -----------------------------------------------------------------------------
# 2) nginx 기동
# -----------------------------------------------------------------------------
echo "[2/6] nginx 컨테이너 기동..."
dc up -d nginx
sleep 3

# -----------------------------------------------------------------------------
# 3) 더미 인증서 삭제 (certbot이 새로 만들기 위해)
# -----------------------------------------------------------------------------
echo "[3/6] 더미 인증서 삭제..."
dc run --rm --entrypoint "\
    sh -c 'rm -rf /etc/letsencrypt/live/${PRIMARY_DOMAIN} && \
           rm -rf /etc/letsencrypt/archive/${PRIMARY_DOMAIN} && \
           rm -rf /etc/letsencrypt/renewal/${PRIMARY_DOMAIN}.conf'" certbot

# -----------------------------------------------------------------------------
# 4) 스테이징 발급 (Rate Limit 회피)
# -----------------------------------------------------------------------------
echo "[4/6] Let's Encrypt 스테이징 환경 발급 시도..."
dc run --rm --entrypoint "\
    certbot certonly --webroot -w /var/www/certbot \
        --staging \
        --email ${EMAIL} \
        ${DOMAIN_ARGS} \
        --rsa-key-size ${RSA_KEY_SIZE} \
        --agree-tos \
        --no-eff-email \
        --force-renewal" certbot

if [[ "$STAGING" == "1" ]]; then
    echo
    echo "STAGING=1 이므로 스테이징 발급만 수행하고 종료합니다."
    echo "프로덕션 발급을 원하시면 STAGING=0 으로 다시 실행하세요."
    exit 0
fi

# -----------------------------------------------------------------------------
# 5) 프로덕션 발급
# -----------------------------------------------------------------------------
echo "[5/6] 스테이징 인증서 삭제 후 프로덕션 발급..."
dc run --rm --entrypoint "\
    sh -c 'rm -rf /etc/letsencrypt/live/${PRIMARY_DOMAIN} && \
           rm -rf /etc/letsencrypt/archive/${PRIMARY_DOMAIN} && \
           rm -rf /etc/letsencrypt/renewal/${PRIMARY_DOMAIN}.conf'" certbot

dc run --rm --entrypoint "\
    certbot certonly --webroot -w /var/www/certbot \
        --email ${EMAIL} \
        ${DOMAIN_ARGS} \
        --rsa-key-size ${RSA_KEY_SIZE} \
        --agree-tos \
        --no-eff-email \
        --force-renewal" certbot

# -----------------------------------------------------------------------------
# 6) nginx 재로드 (인증서 인식)
# -----------------------------------------------------------------------------
echo "[6/6] nginx 무중단 재로드..."
dc exec nginx nginx -t
dc exec nginx nginx -s reload

echo
echo "============================================================"
echo " 발급 완료"
echo "============================================================"
echo " 인증서: /etc/letsencrypt/live/${PRIMARY_DOMAIN}/"
echo " 만료일: 90일 후 (renew.sh 가 자동 갱신)"
echo
echo " 다음 단계:"
echo "   1) https://${PRIMARY_DOMAIN}/healthz 응답 확인"
echo "   2) scripts/deploy/ssl-test.sh 로 SSL 등급 점검"
echo "   3) renew.sh 를 cron 또는 systemd timer 에 등록"
echo "============================================================"
