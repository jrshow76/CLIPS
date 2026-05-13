# Let's Encrypt 자동 발급/갱신 가이드

TradePilot 프로덕션은 단일 도메인(`tradepilot.example.com`)에 대해
Let's Encrypt 무료 TLS 인증서를 자동 발급/갱신한다.

## 아키텍처

```
[ 클라이언트 ]
     │ HTTPS
     ▼
┌─────────────┐    ┌──────────────┐
│   nginx     │◀──▶│  certbot     │
│ (TLS 종단)  │    │ (renewer)    │
│ :80, :443   │    │ webroot 챌린지│
└─────────────┘    └──────────────┘
     │  공유 볼륨: certbot-etc (/etc/letsencrypt)
     │              certbot-www (/var/www/certbot)
     ▼
[ backend / frontend ]  ← 내부 네트워크만
```

## 1. 사전 준비

### 1.1 도메인 및 DNS

A 또는 AAAA 레코드가 nginx를 띄울 호스트 IP를 가리켜야 한다.

| 레코드 | 이름 | 타입 | 값 | TTL |
|---|---|---|---|---|
| 메인 | `tradepilot.example.com` | A | `<서버 공인 IP>` | 300 |
| (선택) www | `www.tradepilot.example.com` | A | `<서버 공인 IP>` | 300 |

DNS 전파 후 다음 명령으로 검증:

```bash
dig +short tradepilot.example.com
nslookup tradepilot.example.com 8.8.8.8
```

### 1.2 방화벽 / 보안그룹

| 포트 | 프로토콜 | 용도 | 출처 |
|---|---|---|---|
| 80  | TCP | ACME http-01 챌린지, HTTP→HTTPS 리디렉션 | 0.0.0.0/0 |
| 443 | TCP | HTTPS                                    | 0.0.0.0/0 |
| 22  | TCP | SSH (관리)                               | 운영자 IP만 |

### 1.3 sysctl / 파일핸들

```bash
# nginx worker_connections 4096 대응
ulimit -n 65536
echo "fs.file-max = 200000" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 1.4 Diffie-Hellman 파라미터 생성

```bash
openssl dhparam -out infra/nginx/ssl/dhparam.pem 2048
chmod 600 infra/nginx/ssl/dhparam.pem
```

자세한 내용은 `infra/nginx/dhparam.pem.note.md` 참조.

## 2. 최초 발급 (5단계)

```bash
cd /home/user/CLIPS/TradePilot

# 1단계: 환경변수 준비
cp .env.example .env
# .env 편집 후

# 2단계: (옵션) 스테이징 환경 먼저 검증
sudo DOMAIN=tradepilot.example.com \
     EMAIL=admin@tradepilot.example.com \
     STAGING=1 \
     bash infra/letsencrypt/init-letsencrypt.sh

# 3단계: 프로덕션 발급 (Rate Limit 주의: 도메인당 주 50회)
sudo DOMAIN=tradepilot.example.com \
     EMAIL=admin@tradepilot.example.com \
     bash infra/letsencrypt/init-letsencrypt.sh

# 4단계: 검증
curl -I https://tradepilot.example.com/healthz
bash scripts/deploy/ssl-test.sh tradepilot.example.com

# 5단계: 자동 갱신 cron 등록
sudo crontab -e
# 다음 줄 추가:
# 0 3 * * * /home/user/CLIPS/TradePilot/infra/letsencrypt/renew.sh >> /var/log/letsencrypt-renew.log 2>&1
```

## 3. 자동 갱신

`renew.sh` 는 매일 03:00에 실행되며, 만료까지 30일 이내 인증서만 실제로 갱신한다.
갱신 성공 시 nginx 무중단 재로드(`nginx -s reload`)가 자동 실행된다.

### 갱신 검증 (수동)

```bash
# Dry run (실제 갱신 없이 시뮬레이션)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    run --rm --entrypoint "certbot renew --dry-run" certbot
```

### 만료일 확인

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    exec nginx openssl x509 -in /etc/letsencrypt/live/tradepilot.example.com/fullchain.pem -noout -dates
```

## 4. 트러블슈팅

### Q. ACME 챌린지 실패 (`Connection refused` / `404`)

- 80 포트가 nginx에 포워딩되는지 확인 (`docker compose ps nginx`).
- `/.well-known/acme-challenge/` 위치 블록이 conf.d/tradepilot.conf 에 있는지 확인.
- 방화벽이 80을 막고 있지 않은지 확인 (`curl -v http://tradepilot.example.com/.well-known/acme-challenge/test`).

### Q. Rate Limit 초과 (`too many certificates already issued`)

- 7일 후 자동 해제. 또는 `--staging` 으로 스테이징에서 충분히 테스트할 것.
- Let's Encrypt 한도: 도메인당 주 50개 인증서, 동일 도메인 세트 5회 중복 발급.

### Q. nginx 재로드 후 인증서 변경이 반영되지 않음

- 컨테이너 안에서 직접 확인: `docker exec tp-nginx ls -la /etc/letsencrypt/live/<도메인>/`
- 심볼릭 링크가 깨졌다면: `certbot certificates` 실행 후 결과 확인.

### Q. OCSP stapling 안 됨

- `nginx -T | grep ssl_trusted_certificate` 로 chain.pem 경로 확인.
- DNS resolver 가 OCSP responder 에 도달 가능한지 확인 (방화벽 egress).

## 5. 갱신 실패 시 알림 (선택)

`renew.sh` 의 종료 코드를 모니터링 시스템(Prometheus textfile, Sentry cron 등)에 연동.

예 (Prometheus node_exporter textfile):

```bash
#!/usr/bin/env bash
/path/to/renew.sh
echo "letsencrypt_last_renew_exit_code $?" > /var/lib/node_exporter/letsencrypt.prom
echo "letsencrypt_last_renew_timestamp $(date +%s)" >> /var/lib/node_exporter/letsencrypt.prom
```
