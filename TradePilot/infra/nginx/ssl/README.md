# SSL 디렉토리

이 디렉토리는 nginx의 TLS 관련 보조 파일을 보관한다.

## 파일 목록

| 파일 | 용도 | 생성 방법 | Git 커밋 |
|---|---|---|---|
| `options-ssl-nginx.conf` | Mozilla Intermediate 권장 cipher / 프로토콜 | 본 저장소 동봉 | O |
| `dhparam.pem` | Diffie-Hellman 파라미터 (PFS) | `openssl dhparam` 직접 생성 | X (gitignore) |

## 인증서 발급/배치

실제 인증서(`fullchain.pem`, `privkey.pem`, `chain.pem`)는 **이 디렉토리가 아니라**
Let's Encrypt 표준 경로(`/etc/letsencrypt/live/<domain>/`)에 배치한다.

발급 절차는 다음 문서를 따른다:

- `infra/letsencrypt/README.md` - Let's Encrypt 발급 절차 전체
- `infra/letsencrypt/init-letsencrypt.sh` - 최초 발급 스크립트 (스테이징 → 프로덕션)
- `infra/letsencrypt/renew.sh` - 갱신 스크립트 (cron 등록용)

## nginx 컨테이너 볼륨 매핑

`docker-compose.prod.yml` 발췌:

```yaml
nginx:
  volumes:
    - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./infra/nginx/conf.d:/etc/nginx/conf.d:ro
    - ./infra/nginx/ssl:/etc/nginx/ssl:ro              # 본 디렉토리
    - ./infra/nginx/html:/usr/share/nginx/html:ro      # 에러 페이지
    - certbot-etc:/etc/letsencrypt:ro                  # 인증서 (certbot이 쓴 것 읽기)
    - certbot-www:/var/www/certbot:ro                  # ACME webroot
    - nginx-logs:/var/log/nginx
```

## 권한

```bash
chmod 644 options-ssl-nginx.conf
chmod 600 dhparam.pem        # private 정보로 취급
```

## 보안 체크리스트

- [ ] `dhparam.pem` 이 git에 커밋되지 않았다
- [ ] `privkey.pem` 권한이 600 이하 (root 또는 nginx 사용자만 읽기)
- [ ] OCSP stapling용 `chain.pem` 경로가 `options-ssl-nginx.conf`의 `ssl_trusted_certificate` 와 일치
- [ ] TLS 1.0 / 1.1 비활성화 (`ssl_protocols TLSv1.2 TLSv1.3;`)
- [ ] 약한 cipher (RC4, 3DES, MD5) 미포함
- [ ] HSTS preload 등록 전이면 `preload` 토큰 제거
