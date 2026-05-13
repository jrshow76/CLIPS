# TradePilot 시크릿 관리 정책

> 문서 ID: 73_SECRETS_POLICY
> 버전: v1.0
> 작성자: QA (Security Review)
> 검토자: PM, DevLead, DBA
> 최종 수정일: 2026-05-13

본 문서는 TradePilot의 모든 시크릿(JWT, AES, DB, API Key, GPG, IAM)의 분류, 저장 위치, 회전 주기, 누출 사고 대응을 정의한다.

---

## 1. 시크릿 분류 (Tier)

### Tier-0 (Critical) — 자본/계정 직결
- `JWT_SECRET` — 모든 사용자 JWT 위조 가능
- `AES_KEY` — CREON 계좌 비밀번호 등 민감 문자열 복호화
- `CREON_GATEWAY_API_KEY` — 실거래 발주 권한
- DB SUPERUSER 비밀번호 (`postgres`)
- AWS Root / 백업 IAM 계정 자격증명

### Tier-1 (High) — 시스템 침해 가능
- `POSTGRES_PASSWORD` (애플리케이션 계정)
- `REDIS_PASSWORD` (현재 미사용 → 도입 권장)
- `SMTP_PASSWORD`
- `SENTRY_DSN` (DSN 자체는 누출되어도 데이터 쓰기만 가능)
- GPG 백업 암호화 개인키
- TLS 인증서 개인키 (`/etc/letsencrypt/live/.../privkey.pem`)

### Tier-2 (Medium) — 운영 영향
- `TELEGRAM_BOT_TOKEN`
- 외부 데이터 소스 API Key (KRX 등)
- CI/CD secrets (GHCR_TOKEN, AWS_ACCESS_KEY)

### Tier-3 (Low) — 비기능적
- 개발 환경 `.env`의 placeholder 값 (절대 운영 사용 금지)

---

## 2. 환경별 시크릿 분리

| 환경 | JWT_SECRET | AES_KEY | DB Password | Gateway API Key |
|---|---|---|---|---|
| 개발(local) | 고정 placeholder OK | 고정 placeholder OK | tradepilot | placeholder |
| 테스트(CI) | 테스트 전용 시크릿 | 테스트 전용 | postgres-test | mock |
| 스테이징 | 운영과 별도 발급 (32+자 랜덤) | 별도 | 별도 | 별도 |
| 운영 | 운영 전용 (32+자 랜덤) | 32바이트 base64 랜덤 | 16+자 랜덤 | 32+자 랜덤 |

**원칙**: 환경 간 시크릿 절대 공유 금지. 운영 시크릿이 스테이징/CI에 유출되면 운영 침해와 동일 취급.

---

## 3. 시크릿 저장 마이그레이션 로드맵

### 3.1 현재 상태 (As-Is)
- `.env` 파일에 평문 보관
- docker-compose 환경변수로 컨테이너 주입
- 호스트 파일시스템에 600 권한

### 3.2 단기 (1개월) — Docker Swarm Secrets
```yaml
# docker-compose.prod.yml
secrets:
  jwt_secret:
    external: true
  aes_key:
    external: true
  creon_gateway_api_key:
    external: true

services:
  backend-api:
    secrets:
      - jwt_secret
      - aes_key
      - creon_gateway_api_key
    environment:
      JWT_SECRET_FILE: /run/secrets/jwt_secret
      AES_KEY_FILE: /run/secrets/aes_key
      CREON_GATEWAY_API_KEY_FILE: /run/secrets/creon_gateway_api_key
```

백엔드 코드 변경:
```python
# backend/app/core/config.py
import os

def _read_secret_or_env(name: str, default: str = "") -> str:
    file_path = os.environ.get(f"{name}_FILE")
    if file_path and os.path.isfile(file_path):
        with open(file_path) as f:
            return f.read().strip()
    return os.environ.get(name, default)

# Settings 정의 시 활용
JWT_SECRET: str = Field(default_factory=lambda: _read_secret_or_env("JWT_SECRET", "..."))
```

생성:
```bash
echo -n "$(openssl rand -base64 48)" | docker secret create jwt_secret -
echo -n "$(openssl rand -base64 32)" | docker secret create aes_key -
echo -n "$(openssl rand -hex 32)"    | docker secret create creon_gateway_api_key -
```

### 3.3 중기 (분기) — HashiCorp Vault
- Vault Agent Sidecar 패턴 (컨테이너 시작 시 시크릿 fetch)
- Dynamic Secrets (DB 비밀번호 1시간 TTL 자동 회전)
- Audit Log 자동화

```hcl
# Vault 정책 예시
path "secret/data/tradepilot/prod/*" {
  capabilities = ["read"]
}
path "database/creds/tradepilot-app" {
  capabilities = ["read"]
}
```

### 3.4 장기 (반기+) — KMS/HSM
- AWS KMS / GCP Cloud KMS로 마스터 키 보관
- Envelope Encryption (DEK는 KMS로 wrapping)
- HSM 도입은 매매 자본 규모에 따라 결정

---

## 4. 회전 주기 (Rotation)

| 시크릿 | 회전 주기 | 비상 회전 트리거 |
|---|---|---|
| JWT_SECRET | **90일** | 누출 의심, 직원 퇴사(접근 권한 보유자) |
| AES_KEY | **1년** | 누출 의심 (AES 키 변경 시 기존 암호화 데이터 마이그레이션 필수) |
| CREON_GATEWAY_API_KEY | **180일** | 게이트웨이 호스트 변경, 침해 의심 |
| POSTGRES_PASSWORD | **180일** | DBA 변경 |
| SMTP_PASSWORD | **180일** | SMTP 제공자 정책 변경 시 |
| GPG 백업 키 | **1년** (30일 유예) | 분실/유출 시 즉시 |
| TLS 인증서 | Let's Encrypt 자동(90일) | - |
| AWS IAM Access Key | **90일** | 직원 변경, 키 비활성 |

### 4.1 회전 절차 (JWT_SECRET 예시)
```bash
# 1. 새 시크릿 생성
NEW=$(openssl rand -base64 48)

# 2. 듀얼 키 모드 임시 활성화 (옵션 — 무중단)
#    백엔드 코드에 JWT_SECRET_PRIMARY + JWT_SECRET_SECONDARY 동시 검증 추가
JWT_SECRET_PRIMARY=$NEW
JWT_SECRET_SECONDARY=$OLD

# 3. 새 access 토큰 발급은 PRIMARY로, 기존 토큰은 SECONDARY로 검증
# 4. 30분(access TTL) + 7일(refresh TTL) 경과 후 SECONDARY 제거
# 5. 사용자에게 강제 재로그인 알림 (옵션)
```

### 4.2 AES_KEY 회전 (마이그레이션 포함)
```python
# backend/app/scripts/rotate_aes_key.py (신규 작성 예시)
async def rotate(old_key: str, new_key: str):
    """기존 AES_KEY로 암호화된 모든 데이터를 새 키로 재암호화."""
    rows = await db.execute("SELECT id, creon_password_encrypted FROM users WHERE creon_password_encrypted IS NOT NULL")
    for row in rows:
        plain = aes_decrypt_with_key(row.creon_password_encrypted, old_key)
        new_ct = aes_encrypt_with_key(plain, new_key)
        await db.execute(
            "UPDATE users SET creon_password_encrypted=:ct WHERE id=:id",
            {"ct": new_ct, "id": row.id}
        )
```

---

## 5. 누출 사고 대응 (Secrets Leak)

### 5.1 즉시 대응 (1시간 내)

| 누출된 시크릿 | 즉시 조치 |
|---|---|
| JWT_SECRET | (1) 메인터넌스 모드 ON (2) 새 시크릿 생성 (3) 모든 세션 폐기 (4) 컨테이너 재시작 |
| AES_KEY | (1) 메인터넌스 모드 ON (2) 새 키 + 기존 데이터 재암호화 스크립트 (3) 컨테이너 재시작 |
| CREON_GATEWAY_API_KEY | (1) 게이트웨이 격리 (2) 새 키 발급 (3) 본체+게이트웨이 동시 갱신 |
| DB Password | (1) 새 비밀번호 설정 (2) 모든 백엔드 컨테이너 재시작 |
| GPG 키 | (1) 새 키페어 생성 (2) 새 백업부터 새 키 사용 (3) 구 키 archive (복구용 보관) |
| AWS IAM | (1) 즉시 키 비활성 (2) 새 키 발급 (3) 영향 분석 (CloudTrail 조회) |
| TLS 인증서 키 | (1) 인증서 즉시 폐기 (CRL/OCSP) (2) 새 인증서 발급 (Let's Encrypt) (3) 다운타임 최소화 |

### 5.2 중기 (24시간 내)
- RCA 작성 (`72_security_checklist.md` §4.5)
- 영향 받은 사용자/거래 통보
- 금융 규제 보고 (필요 시)
- 보안 팀 회의 + 재발 방지 액션

### 5.3 장기 (1주 내)
- 로깅/모니터링 강화
- 본 정책 갱신
- 외부 펜테스트 의뢰 검토

---

## 6. 시크릿 탐지 자동화

### 6.1 Pre-commit Hook
```bash
# .git/hooks/pre-commit
#!/bin/bash
gitleaks detect --source . --no-git --exit-code 1 || {
  echo "ERROR: 시크릿 패턴 발견. 커밋 차단."
  exit 1
}
```

### 6.2 CI 자동 스캔
- `tradepilot-security.yml` 워크플로우에 gitleaks job 존재 ✅
- PR 시 자동 차단

### 6.3 운영 환경 정기 스캔
- 월 1회 `gitleaks` 전체 히스토리 스캔
- 분기 1회 외부 도구(TruffleHog, Trivy secret) 교차 검증

---

## 7. 접근 권한 (RBAC)

### 7.1 시크릿 접근 권한 매트릭스

| 시크릿 | PM | DevLead | BackendSenior | DBA | DevOps |
|---|:---:|:---:|:---:|:---:|:---:|
| JWT_SECRET | R | R | R | - | RW |
| AES_KEY | R | R | R | - | RW |
| CREON_GATEWAY_API_KEY | R | R | R | - | RW |
| DB SUPERUSER | - | R | - | RW | R |
| 애플리케이션 DB | - | R | R | RW | RW |
| GPG 백업 키 (개인키) | - | - | - | RW (오프라인) | - |
| AWS Root | RW | - | - | - | - |
| AWS IAM (백업 사용자) | R | R | - | R | RW |

### 7.2 접근 감사
- 모든 시크릿 조회는 Vault audit log (도입 후) 또는 호스트 syslog로 기록
- 분기 1회 PM이 접근 이력 검토

---

## 8. 시크릿 안티패턴 (절대 금지)

- ❌ Git 저장소에 `.env` 커밋
- ❌ Slack/Notion/이메일에 평문 시크릿 공유
- ❌ Docker 이미지 빌드 시점에 ARG로 주입(`docker history`로 추출 가능)
- ❌ 환경변수 dump 로깅 (`log.info(env=os.environ)`)
- ❌ 디버거/Sentry 컨텍스트에 시크릿 포함
- ❌ 모든 환경에 동일 시크릿 재사용
- ❌ 시크릿을 URL 쿼리 파라미터로 전달 (로그 노출)
- ❌ HTTP 요청 본문에 평문 비밀번호 (HTTPS 외 환경)

---

## 9. 검증 체크리스트

### 9.1 신규 시크릿 도입 시
- [ ] Tier 분류 확정
- [ ] 환경별 분리 (dev/staging/prod 별도 값)
- [ ] 회전 주기 정의 + 캘린더 등록
- [ ] 누출 시 대응 절차 문서화
- [ ] `.env.example`에 placeholder만 추가
- [ ] 코드에서 절대 로깅하지 않도록 검토

### 9.2 운영 진입 전
- [ ] 본 정책의 모든 시크릿이 placeholder가 아님
- [ ] `_validate_production_settings()` 통과
- [ ] gitleaks 전체 히스토리 통과
- [ ] 회전 캘린더 등록 완료

---

## 10. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-13 | QA (Security Review) | 최초 작성 - Tier 분류 + 회전 + Vault 마이그레이션 |
