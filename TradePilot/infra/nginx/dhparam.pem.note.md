# Diffie-Hellman 파라미터(dhparam.pem) 발급 가이드

`ssl_dhparam` 지시자가 가리키는 `dhparam.pem` 파일은 **반드시 서버에서 직접 생성**해야 한다.
타인이 만들어준 파일을 사용하면 PFS(Perfect Forward Secrecy) 보장이 약해진다.

## 1. 생성 명령

운영 서버에서 한 번만 실행한다(약 1~5분 소요).

```bash
# 2048비트 (권장, SSL Labs A+ 충분)
openssl dhparam -out /home/user/CLIPS/TradePilot/infra/nginx/ssl/dhparam.pem 2048

# 보안 강화가 필요하면 4096비트 (생성 시간 30분 이상 가능)
# openssl dhparam -out /home/user/CLIPS/TradePilot/infra/nginx/ssl/dhparam.pem 4096
```

## 2. 권한

```bash
chmod 600 /home/user/CLIPS/TradePilot/infra/nginx/ssl/dhparam.pem
chown root:root /home/user/CLIPS/TradePilot/infra/nginx/ssl/dhparam.pem
```

## 3. nginx 컨테이너 마운트

`docker-compose.prod.yml` 에서 다음과 같이 마운트한다(이미 설정됨):

```yaml
volumes:
  - ./infra/nginx/ssl:/etc/nginx/ssl:ro
```

컨테이너 내부 경로: `/etc/nginx/ssl/dhparam.pem`

## 4. 갱신 주기

DH 파라미터는 **사실상 영구**이지만, 보수적으로 **2~3년 주기로 재생성**을 권장한다.
재생성 후 `nginx -s reload` 만 수행하면 무중단 적용된다.

## 5. .gitignore

`dhparam.pem` 은 절대 Git에 커밋하지 않는다.
프로젝트 `.gitignore` 에 다음이 포함되어 있는지 확인한다:

```gitignore
infra/nginx/ssl/dhparam.pem
infra/nginx/ssl/*.pem
```

## 6. 검증

생성 후 정상 여부 확인:

```bash
openssl dhparam -in /home/user/CLIPS/TradePilot/infra/nginx/ssl/dhparam.pem -text -noout | head -3
# DH Parameters: (2048 bit) ... 출력 확인
```
