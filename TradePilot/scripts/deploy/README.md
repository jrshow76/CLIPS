# 배포 스크립트

TradePilot 프로덕션 배포·운영용 셸 스크립트 모음.

## 파일 목록

| 스크립트 | 용도 | 호출 시점 |
|---|---|---|
| `prod-up.sh` | 프로덕션 스택 기동 (compose up -d) | 배포 시 |
| `reload-nginx.sh` | nginx 무중단 재로드 | 설정 변경 후 |
| `ssl-test.sh` | SSL 등급/헤더 점검 | 발급 직후, 주기 점검 |

## 사전 조건

1. `.env` 파일 작성 (`.env.example` 참조)
2. Diffie-Hellman 파라미터 생성 (`infra/nginx/dhparam.pem.note.md`)
3. Let's Encrypt 인증서 발급 (`infra/letsencrypt/init-letsencrypt.sh`)
4. DNS A 레코드 등록 + 80/443 방화벽 개방

## 일반 사용 흐름

```bash
# 1. 최초 배포
cp .env.example .env                                              # 값 채우기
openssl dhparam -out infra/nginx/ssl/dhparam.pem 2048
sudo DOMAIN=tradepilot.example.com EMAIL=admin@example.com \
     bash infra/letsencrypt/init-letsencrypt.sh
bash scripts/deploy/prod-up.sh --build

# 2. nginx 설정만 변경 후 재로드
vim infra/nginx/conf.d/tradepilot.conf
bash scripts/deploy/reload-nginx.sh

# 3. SSL 등급 점검
bash scripts/deploy/ssl-test.sh tradepilot.example.com
bash scripts/deploy/ssl-test.sh tradepilot.example.com --labs   # SSL Labs API
```

## 권한

```bash
chmod +x scripts/deploy/*.sh
```

## 0-down 재배포 절차

| 단계 | 명령 | 확인 |
|---|---|---|
| 1 | 새 이미지 pull/build | `docker compose ... pull frontend backend-api` |
| 2 | 백엔드 롤링 업데이트 | `docker compose ... up -d --no-deps backend-api` (워커 graceful) |
| 3 | 프론트 롤링 업데이트 | `docker compose ... up -d --no-deps frontend` |
| 4 | nginx 재로드 (필요 시) | `bash scripts/deploy/reload-nginx.sh` |
| 5 | 헬스 검증 | `curl -fs https://<domain>/healthz` |

## 트러블슈팅

- nginx 기동 실패 → `docker compose logs nginx` 에서 `nginx -t` 메시지 확인
- 502 Bad Gateway → backend-api/frontend 컨테이너가 healthy 인지 확인
- 504 Gateway Timeout → `proxy_read_timeout` 조정, 백엔드 슬로우 쿼리 점검
- SSL Handshake Failure → `infra/nginx/ssl/dhparam.pem` 존재 / 권한 확인
