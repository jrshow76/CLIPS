# TradePilot nginx 리버스 프록시 + TLS 가이드

> 문서 ID: 41_NGINX_TLS_GUIDE
> 버전: v1.0
> 작성자: DevLead
> 검토자: BackendSenior, QA, PM
> 최종 수정일: 2026-05-13

본 문서는 TradePilot 프로덕션 환경의 외부 진입점인 nginx 리버스 프록시와 Let's Encrypt 기반 TLS 종단 구성을 정의한다.
모든 외부 트래픽은 단일 도메인(`tradepilot.example.com`)으로 들어와 nginx에서 TLS 종단 후 내부 서비스로 라우팅된다.

---

## 1. 아키텍처

```
                          ┌────────────────────────────────┐
                          │   Public Internet              │
                          │   (브라우저 / 모바일앱)           │
                          └──────────────┬─────────────────┘
                                         │ HTTPS (443)
                                         │ HTTP  (80, → 301 HTTPS)
                                         ▼
                          ┌────────────────────────────────┐
                          │   nginx (TLS 종단)              │
                          │   - HSTS / 보안 헤더            │
                          │   - Rate Limit                 │
                          │   - WebSocket Upgrade          │
                          │   - 정적 캐싱 (Next.js _next)   │
                          │   - JSON 액세스 로그            │
                          └─────┬─────────┬───────────┬────┘
                                │         │           │
              /api/v1/* /ws/*  │         │ /metrics  │ /
              /healthz         │         │           │
                                ▼         ▼           ▼
                      ┌──────────────┐ (사설망만) ┌──────────────┐
                      │  backend-api │ ────────  │  frontend    │
                      │  :8000       │           │  Next.js :3000│
                      │  FastAPI     │           │  (standalone) │
                      └──────┬───────┘           └──────────────┘
                             │
                ┌────────────┼─────────────┐
                ▼            ▼             ▼
            postgres      redis       celery worker
            (internal)    (internal)  (internal)
```

**핵심 설계 결정**

- **단일 진입점**: 80/443 외 모든 포트는 호스트에 노출하지 않음.
- **TLS 종단을 nginx 단일 지점에서**: 백엔드는 평문 HTTP만 처리 (성능/단순화).
- **certbot은 별도 컨테이너**: nginx와 `certbot-etc` 볼륨 공유, 갱신 시에만 nginx 재로드.
- **Path 라우팅**: 도메인 분리 대신 Path 기반 → 인증서 1장으로 운영.
- **WebSocket: 동일 도메인**: 프론트는 `wss://<domain>/ws/...` 로 same-origin 호출.

---

## 2. 라우팅 표

| Location | 업스트림 | 인증 | Rate Limit | 캐시 | 비고 |
|---|---|---|---|---|---|
| `GET /healthz` | backend-api:8000 | 무 | 없음 | 없음 | LB 헬스 체크 |
| `GET /readyz`  | backend-api:8000 | 무 | 없음 | 없음 | 준비도 체크 |
| `GET /metrics` | backend-api:8000 | 무 (사설망 화이트리스트) | 없음 | 없음 | Prometheus scrape, **외부 deny** |
| `POST /api/v1/auth/login` | backend-api:8000 | 무 | **5 req/min** (zn_login) | 없음 | 브루트포스 방어 |
| `* /api/v1/orders/*` | backend-api:8000 | JWT | **3 req/s, burst 5** (zn_order) | 없음 | 시장가 폭주 방어 |
| `* /api/v1/*` | backend-api:8000 | JWT (라우터별) | **10 req/s, burst 20** (zn_api) | 없음 | 일반 REST API |
| `WS /ws/*` | backend-api:8000 (Upgrade) | JWT (쿼리/헤더) | **20 conn/s, burst 40** (zn_ws) | 없음 | `proxy_read_timeout 3600s`, 버퍼링 OFF |
| `GET /_next/static/*` | frontend:3000 | 무 | 없음 | **365d immutable** | 해시 파일명 |
| `GET /_next/image` | frontend:3000 | 무 | 없음 | **7d + SWR 1d** | 이미지 최적화 |
| `GET /favicon.ico, /robots.txt, ...` | frontend:3000 | 무 | 없음 | **1d + SWR 1h** | 표준 정적 자산 |
| `* /` | frontend:3000 | 무 (페이지별) | 없음 (Next.js 자체) | (Next 응답 헤더 따름) | SSR/CSR/ISR |

**전체 동시 접속 한도**: IP당 100 (`limit_conn zn_conn 100`)

---

## 3. 보안 헤더 카탈로그

| 헤더 | 값 | 효과 | 비고 |
|---|---|---|---|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | TLS 강제 (2년) | preload 등록 전엔 토큰 제거 |
| `X-Frame-Options` | `DENY` | 클릭재킹 방지 | iframe 삽입 일체 차단 |
| `X-Content-Type-Options` | `nosniff` | MIME 스니핑 방어 | |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | 외부 이동 시 origin만 노출 | |
| `X-XSS-Protection` | `1; mode=block` | 구형 브라우저 보호 | 모던에선 CSP가 우선 |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=(), payment=(), ...` | 위험 권한 명시적 차단 | 트레이딩 앱 특성상 모두 차단 |
| `Cross-Origin-Opener-Policy` | `same-origin` | Spectre 류 방어 | |
| `Cross-Origin-Resource-Policy` | `same-site` | 리소스 무단 접근 차단 | |
| `Content-Security-Policy-Report-Only` | (아래 정책) | XSS / 인젝션 방어 | **초기 Report-Only 권장** |

### CSP 정책 (Report-Only로 시작)

```
default-src 'self';
script-src  'self' 'unsafe-inline' 'unsafe-eval';   # Next.js hydration 호환
style-src   'self' 'unsafe-inline';
img-src     'self' data: blob: https:;
font-src    'self' data:;
connect-src 'self' wss: https:;                     # WebSocket 포함
frame-ancestors 'none';
base-uri    'self';
form-action 'self';
report-uri  /csp-report
```

### CSP 튜닝 절차 (3단계)

1. **수집기 구축**: 백엔드 `POST /csp-report` 라우트가 위반 보고 JSON을 수집/집계.
2. **Report-Only 1~2주 운영**: 위반 사례 수집 후 정책 미세 조정.
3. **Enforce 전환**: `Content-Security-Policy` 로 헤더명 변경.

> 운영 안정화 후 nonce 기반 script-src로 강화하면 `'unsafe-inline'` 제거 가능 (Next.js 13+ 지원).

---

## 4. Rate Limit 정책

| Zone | 한도 | Burst | nodelay | 적용 location | 의도 |
|---|---|---|---|---|---|
| `zn_login` | 5 req/**min** | 3 | yes | `/api/v1/auth/login` | 로그인 브루트포스 방어 |
| `zn_order` | 3 req/s | 5 | yes | `/api/v1/orders` | 주문 폭주/오류 방어 |
| `zn_api` | 10 req/s | 20 | yes | `/api/v1/*` | 일반 API DoS 방어 |
| `zn_public` | 30 req/s | (미적용) | - | 시세/지수 (예약) | 공개 GET 한도 |
| `zn_ws` | 20 conn/s | 40 | yes | `/ws/*` (handshake만) | WS 핸드셰이크 폭주 방어 |
| `zn_conn` | 동시 100 conn | - | - | 전체 server | IP당 동시 연결 한도 |

키: `$binary_remote_addr` (IPv4 4B / IPv6 16B → 10MB 존당 약 16만 IP 추적).

초과 시 `429 Too Many Requests` + 커스텀 에러 페이지(`/usr/share/nginx/html/errors/429.html`).

> 백엔드의 RateLimit 미들웨어와 **이중 방어** 구성: nginx는 IP 단, 백엔드는 사용자 단(JWT sub).

---

## 5. WebSocket 주의사항

WebSocket 라우팅에서 누락 시 흔한 장애:

| 누락 | 증상 |
|---|---|
| `proxy_http_version 1.1;` | 101 Switching Protocols 미발생, 일반 HTTP로 오인 |
| `proxy_set_header Upgrade $http_upgrade;` | 핸드셰이크 실패 (백엔드가 ws로 인식 못함) |
| `proxy_set_header Connection "upgrade";` | 동일. 단, 변수 `$connection_upgrade` 권장 |
| `proxy_read_timeout 60s` (기본) | 60초 idle 후 nginx가 강제 종료 → 재연결 폭주 |
| `proxy_buffering off` 미설정 | 실시간 푸시 지연 (수백 ms) |

본 설정에서는 모두 적용함:

```nginx
location /ws/ {
    proxy_http_version 1.1;
    proxy_set_header   Upgrade    $http_upgrade;
    proxy_set_header   Connection $connection_upgrade;
    proxy_read_timeout    3600s;
    proxy_send_timeout    3600s;
    proxy_connect_timeout 30s;
    proxy_buffering off;
    gzip off;
}
```

`$connection_upgrade` 변수는 `nginx.conf` 의 `map`으로 정의:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
```

---

## 6. 인증서 발급 5단계

```bash
# 1단계: 환경변수 / DH 파라미터 준비
cp .env.example .env                                              # 값 채우기
openssl dhparam -out infra/nginx/ssl/dhparam.pem 2048
chmod 600 infra/nginx/ssl/dhparam.pem

# 2단계: 스테이징 발급으로 검증 (Rate Limit 안전)
sudo DOMAIN=tradepilot.example.com \
     EMAIL=admin@tradepilot.example.com \
     STAGING=1 \
     bash infra/letsencrypt/init-letsencrypt.sh

# 3단계: 프로덕션 발급
sudo DOMAIN=tradepilot.example.com \
     EMAIL=admin@tradepilot.example.com \
     bash infra/letsencrypt/init-letsencrypt.sh

# 4단계: 등급/헤더 검증
bash scripts/deploy/ssl-test.sh tradepilot.example.com
bash scripts/deploy/ssl-test.sh tradepilot.example.com --labs    # SSL Labs API

# 5단계: 자동 갱신 등록 (cron 또는 systemd timer)
sudo crontab -e
# 0 3 * * * /home/user/CLIPS/TradePilot/infra/letsencrypt/renew.sh >> /var/log/letsencrypt-renew.log 2>&1
```

---

## 7. 0-down 재로드 절차

설정 변경 후 무중단 재로드 절차:

| 단계 | 명령 | 검증 |
|---|---|---|
| 1 | 변경 파일 저장 (예: `infra/nginx/conf.d/tradepilot.conf`) | `git diff` |
| 2 | 문법 검증 | `docker compose ... exec nginx nginx -t` |
| 3 | 무중단 재로드 | `bash scripts/deploy/reload-nginx.sh` |
| 4 | 헬스 체크 | `curl -fs https://<domain>/healthz` |
| 5 | 5xx 모니터링 (1분) | Grafana / Sentry / 액세스 로그 grep |

`nginx -s reload` 동작 원리:
- master 프로세스가 새 worker를 fork → 새 요청은 신 worker가 처리.
- 기존 worker는 처리 중 요청을 끝낸 후 graceful 종료(기본 30s).
- 클라이언트 입장에서 다운타임 0.

문법 오류로 재로드 실패 시 기존 worker가 계속 동작 → 안전.

---

## 8. SSL Labs A+ 달성 체크리스트

| 항목 | 본 설정 적용 여부 | 검증 명령 |
|---|---|---|
| TLS 1.2 + 1.3만 | YES | `openssl s_client -tls1` 실패 확인 |
| 약한 cipher 차단 (RC4/3DES/MD5) | YES | `nmap --script ssl-enum-ciphers` |
| Forward Secrecy (ECDHE/DHE만) | YES | `openssl s_client` 의 Server Temp Key 확인 |
| AEAD cipher 우선 (GCM/CHACHA20) | YES | 협상된 cipher 확인 |
| `ssl_prefer_server_ciphers on` | YES | nginx.conf |
| HSTS max-age ≥ 1년 | **2년** | `curl -I` |
| HSTS includeSubDomains | YES | `curl -I` |
| HSTS preload | YES (등록 시) | https://hstspreload.org |
| OCSP Stapling | YES | `openssl s_client -status` |
| DH params ≥ 2048bit | YES | `openssl dhparam -in dhparam.pem -text` |
| 인증서 체인 완전성 | YES (Let's Encrypt fullchain) | SSL Labs |
| SNI 정상 응답 | YES | `openssl s_client -servername` |
| TLS 세션 티켓 OFF | YES (PFS 강화) | `ssl_session_tickets off` |
| 보안 헤더 풀세트 | YES | `securityheaders.com` |

**결과 예상**: SSL Labs A+ (95+/100), Mozilla Observatory A+ (100+점).

---

## 9. 운영 체크리스트 (월간)

- [ ] `bash scripts/deploy/ssl-test.sh <domain>` 실행 → 모든 항목 OK
- [ ] 인증서 만료까지 ≥ 30일 (자동 갱신 정상 동작 확인)
- [ ] `/var/log/letsencrypt-renew.log` 마지막 실행 < 25시간 전
- [ ] nginx 액세스 로그의 5xx 비율 < 0.1%
- [ ] 429 응답 비율 모니터링 → Rate Limit 임계 조정 검토
- [ ] CSP Report-Only 위반 보고 검토 → enforce 전환 가능 여부 판단
- [ ] HSTS Preload 등록 상태 확인 (https://hstspreload.org/?domain=...)
- [ ] DH 파라미터 생성 후 ≥ 2년 경과 시 재생성 검토

---

## 10. 트러블슈팅 매트릭스

| 증상 | 원인 후보 | 대처 |
|---|---|---|
| 502 Bad Gateway | backend-api 다운 / unhealthy | `docker compose logs backend-api`, `docker compose ps` |
| 504 Gateway Timeout | 백엔드 응답 30s 초과 | 슬로우 쿼리 점검, `proxy_read_timeout` 조정 |
| 503 Service Unavailable | nginx upstream 모두 실패 | upstream `max_fails`/`fail_timeout` 조정 |
| 429 Too Many Requests | Rate Limit 초과 | 정상 동작. 사용자 IP 패턴 분석 |
| WS 1006 Abnormal Closure | `proxy_read_timeout` 60s 기본값 | `/ws/` location 의 timeout 확인 |
| 인증서 만료 임박 알림 | renew cron 실패 | `renew.sh` 수동 실행, 로그 확인 |
| SSL Handshake Failure | dhparam.pem 누락 / 권한 문제 | 생성 + 권한 600 |
| Mixed Content 경고 | HTTP 자원 로드 | 프론트엔드 코드에서 `https://` 강제 |
| CSP 위반 다수 | 인라인 스크립트 / 외부 CDN | report-uri 분석 → 정책 추가 |

---

## 11. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-13 | DevLead | 최초 작성 (nginx + Let's Encrypt + WebSocket + Rate Limit + 보안 헤더) |
