#!/usr/bin/env bash
# =============================================================================
# SSL 등급 점검 (SSL Labs A+ 달성 검증)
# -----------------------------------------------------------------------------
# 사용법:
#   bash scripts/deploy/ssl-test.sh tradepilot.example.com
#   bash scripts/deploy/ssl-test.sh tradepilot.example.com --labs   # SSL Labs API
#
# 점검 항목:
#   1. 인증서 체인 / 만료일
#   2. TLS 버전 (1.2, 1.3만 허용 / 1.0, 1.1 거부)
#   3. cipher suite
#   4. HSTS 헤더
#   5. OCSP stapling
#   6. HTTP→HTTPS 리디렉션
#   7. (옵션) SSL Labs API 점수
# =============================================================================

set -uo pipefail

DOMAIN="${1:-tradepilot.example.com}"
USE_LABS="${2:-}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'

ok()   { echo -e "  ${GREEN}OK${RESET}    $*"; }
fail() { echo -e "  ${RED}FAIL${RESET}  $*"; }
warn() { echo -e "  ${YELLOW}WARN${RESET}  $*"; }

echo "============================================================"
echo " SSL 점검: ${DOMAIN}"
echo "============================================================"

# -----------------------------------------------------------------------------
# 1. 인증서 체인 / 만료일
# -----------------------------------------------------------------------------
echo
echo "[1] 인증서 정보"
cert_info=$(echo | openssl s_client -servername "${DOMAIN}" -connect "${DOMAIN}:443" 2>/dev/null \
    | openssl x509 -noout -subject -issuer -dates 2>/dev/null)
if [[ -n "$cert_info" ]]; then
    echo "$cert_info" | sed 's/^/  /'
    expire=$(echo "$cert_info" | grep notAfter | cut -d= -f2-)
    expire_ts=$(date -d "$expire" +%s 2>/dev/null || echo 0)
    now_ts=$(date +%s)
    days_left=$(( (expire_ts - now_ts) / 86400 ))
    if (( days_left > 30 )); then
        ok "인증서 만료까지 ${days_left}일 남음"
    elif (( days_left > 7 )); then
        warn "인증서 만료까지 ${days_left}일 (갱신 임박)"
    else
        fail "인증서 만료까지 ${days_left}일 (즉시 갱신 필요)"
    fi
else
    fail "인증서 정보를 가져올 수 없습니다"
fi

# -----------------------------------------------------------------------------
# 2. TLS 버전 매트릭스
# -----------------------------------------------------------------------------
echo
echo "[2] TLS 프로토콜 매트릭스"
for proto in tls1 tls1_1 tls1_2 tls1_3; do
    result=$(echo | timeout 5 openssl s_client -servername "${DOMAIN}" \
        -connect "${DOMAIN}:443" -"${proto}" 2>&1 | grep -E "Cipher|Protocol|handshake failure|wrong version" | head -2)
    if echo "$result" | grep -qE "Cipher\s*:\s*[A-Z0-9]"; then
        if [[ "$proto" == "tls1" || "$proto" == "tls1_1" ]]; then
            fail "${proto}: 활성화됨 (보안 취약, 비활성화 필요)"
        else
            ok "${proto}: 활성화됨"
        fi
    else
        if [[ "$proto" == "tls1" || "$proto" == "tls1_1" ]]; then
            ok "${proto}: 비활성화됨 (정상)"
        else
            fail "${proto}: 비활성화됨 (활성화 필요)"
        fi
    fi
done

# -----------------------------------------------------------------------------
# 3. Cipher Suite
# -----------------------------------------------------------------------------
echo
echo "[3] 협상된 Cipher"
cipher=$(echo | openssl s_client -servername "${DOMAIN}" -connect "${DOMAIN}:443" 2>/dev/null \
    | grep -E "^\s+Cipher\s+:" | awk '{print $3}')
if [[ -n "$cipher" ]]; then
    case "$cipher" in
        *GCM*|*CHACHA20*|*POLY1305*) ok "Cipher: ${cipher} (AEAD, 권장)" ;;
        *)                            warn "Cipher: ${cipher} (AEAD 아님, 검토 필요)" ;;
    esac
else
    fail "Cipher 협상 실패"
fi

# -----------------------------------------------------------------------------
# 4. HSTS / 보안 헤더
# -----------------------------------------------------------------------------
echo
echo "[4] 보안 헤더"
headers=$(curl -sIk "https://${DOMAIN}/" 2>/dev/null)

check_header() {
    local name="$1"
    local pattern="$2"
    if echo "$headers" | grep -i "^${name}:" | grep -qE "$pattern"; then
        ok "${name}: $(echo "$headers" | grep -i "^${name}:" | head -1 | tr -d '\r')"
    else
        fail "${name}: 누락 또는 부적합"
    fi
}

check_header "Strict-Transport-Security" "max-age=[0-9]+"
check_header "X-Frame-Options" "DENY|SAMEORIGIN"
check_header "X-Content-Type-Options" "nosniff"
check_header "Referrer-Policy" "."
check_header "Permissions-Policy" "."

# CSP는 Report-Only 또는 enforce 둘 다 OK
if echo "$headers" | grep -iE "^Content-Security-Policy(-Report-Only)?:" > /dev/null; then
    ok "Content-Security-Policy: 설정됨"
else
    warn "Content-Security-Policy: 누락 (선택이지만 권장)"
fi

# -----------------------------------------------------------------------------
# 5. OCSP Stapling
# -----------------------------------------------------------------------------
echo
echo "[5] OCSP Stapling"
ocsp=$(echo | openssl s_client -servername "${DOMAIN}" -connect "${DOMAIN}:443" -status 2>/dev/null \
    | grep -A1 "OCSP response" | head -3)
if echo "$ocsp" | grep -q "OCSP Response Status: successful"; then
    ok "OCSP stapling 활성"
else
    warn "OCSP stapling 응답 없음 또는 실패"
fi

# -----------------------------------------------------------------------------
# 6. HTTP → HTTPS 리디렉션
# -----------------------------------------------------------------------------
echo
echo "[6] HTTP → HTTPS 리디렉션"
redirect=$(curl -sI "http://${DOMAIN}/" 2>/dev/null | head -1)
location=$(curl -sI "http://${DOMAIN}/" 2>/dev/null | grep -i "^Location:" | tr -d '\r')
if echo "$redirect" | grep -qE "30[1278]"; then
    ok "리디렉션 응답: $(echo "$redirect" | tr -d '\r')"
    [[ -n "$location" ]] && ok "Location: $(echo "$location" | sed 's/^Location: //I')"
else
    fail "HTTP→HTTPS 리디렉션 미설정"
fi

# -----------------------------------------------------------------------------
# 7. (옵션) SSL Labs API
# -----------------------------------------------------------------------------
if [[ "$USE_LABS" == "--labs" ]]; then
    echo
    echo "[7] SSL Labs API 점수 (수 분 소요)"
    if ! command -v jq >/dev/null; then
        warn "jq 미설치 → SSL Labs 결과 파싱 불가"
    else
        echo "  https://www.ssllabs.com/ssltest/analyze.html?d=${DOMAIN}"
        curl -s "https://api.ssllabs.com/api/v3/analyze?host=${DOMAIN}&publish=off&startNew=on" >/dev/null
        for i in $(seq 1 30); do
            sleep 10
            result=$(curl -s "https://api.ssllabs.com/api/v3/analyze?host=${DOMAIN}")
            status=$(echo "$result" | jq -r '.status')
            echo "  ($i) status=${status}"
            if [[ "$status" == "READY" || "$status" == "ERROR" ]]; then
                grade=$(echo "$result" | jq -r '.endpoints[0].grade // "N/A"')
                echo "  Grade: ${grade}"
                break
            fi
        done
    fi
fi

echo
echo "============================================================"
echo " 점검 완료"
echo "============================================================"
