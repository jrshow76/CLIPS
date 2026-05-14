# TradePilot 시크릿 관리 운영 가이드

> 문서 ID: 43_SECRETS_MANAGEMENT
> 버전: v1.0
> 작성자: BackendDev
> 검토자: DevLead, BackendSenior, DBA
> 최종 수정일: 2026-05-14
> 관련 문서:
>  - 정책: `security/73_secrets_policy.md` (Tier 분류, 회전 주기, RBAC 등 정책 정의)
>  - 보안 리뷰: `security/70_security_review_report.md` (SEC-001, SEC-001-FOLLOWUP)
>  - 런북: `docs/30_operations_runbook.md`

본 문서는 운영자가 매일/주기적으로 따라야 하는 **실무 절차**를 정의한다.
**정책(왜/얼마나/누가)** 은 `73_secrets_policy.md` 를, **절차(어떻게)** 는 본 문서를 참조한다.

---

## 1. 사전 점검 — 운영 진입 전 시크릿 검증

### 1.1 자동 검증 (코드 레벨)

운영 환경(`APP_ENV=production`) 으로 백엔드 컨테이너가 기동될 때
`backend/app/core/config.py` 의 `_validate_production_settings()` 가
다음 항목을 검증하고 실패 시 즉시 fail-fast 한다.

| # | 항목 | 기준 |
|--:|---|---|
| 1 | `JWT_SECRET` | 32자 이상 + 고유문자 16 이상 + 기본값/약한 패턴 아님 |
| 2 | `AES_KEY` | 32자 이상 + 고유문자 16 이상 + 기본값/약한 패턴 아님 |
| 3 | `CREON_GATEWAY_API_KEY` | 32자 이상 + 고유문자 16 이상 + 기본값/약한 패턴 아님 |
| 4 | `DATABASE_URL` | `localhost`/`127.0.0.1`/`postgres` 등 개발 호스트 금지 |
| 5 | `REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_RESULT_URL` | 개발 호스트 금지 |
| 6 | `CORS_ORIGINS` | 와일드카드(`*`) 금지, 빈 값 금지 |
| 7 | `DB_ECHO` | False 강제 (SQL 평문 로그 방지) |
| 8 | `JWT_ALGORITHM` | HS256/384/512 또는 RS256/384/512 화이트리스트 |
| 9 | `SMTP_PASSWORD` | 비어있거나 약한 패턴 아님 |

### 1.2 수동 검증 (배포 직전)

```bash
# 1. .env 파일에 placeholder 가 남아있지 않은지 확인
grep -E '(change-this|replace-with|base64-encoded|change-me|placeholder)' .env && {
  echo "ERROR: .env 에 placeholder 남아있음 — 운영 진입 금지"
  exit 1
}

# 2. gitleaks 로 우발적 시크릿 커밋 여부 점검
gitleaks detect --source . --no-git --exit-code 1

# 3. APP_ENV=production 으로 임시 기동하여 fail-fast 확인
APP_ENV=production python -c "from app.core.config import get_settings; get_settings()"
# RuntimeError 가 발생하지 않아야 정상
```

---

## 2. 시크릿 생성 명령 모음

### 2.1 한 줄 명령 (운영 배포 시 가장 자주 사용)

| 시크릿 | 생성 명령 | 비고 |
|---|---|---|
| `JWT_SECRET` | `openssl rand -hex 32` | 64자 hex (256bit) |
| `AES_KEY` | `openssl rand -base64 32` | 32바이트 base64 (44자) |
| `CREON_GATEWAY_API_KEY` | `openssl rand -hex 32` | 64자 hex |
| `POSTGRES_PASSWORD` | `openssl rand -hex 24` | 48자 hex |
| `SMTP_PASSWORD` | (SMTP 제공자가 발급) | 빈 값이면 SMTP 미사용 |
| `TELEGRAM_BOT_TOKEN` | BotFather 발급 | 빈 값이면 텔레그램 미사용 |
| GPG 백업 키 | `gpg --full-generate-key` (RSA 4096) | 4.1절 참조 |

### 2.2 일괄 생성 스크립트

배포 담당자가 새 환경 구축 시 1회 실행. **출력값은 안전한 채널로만 전달.**

```bash
#!/bin/bash
# scripts/gen_secrets.sh (참고용 — 실제 파일은 별도 PR 로 추가)
set -euo pipefail

echo "JWT_SECRET=$(openssl rand -hex 32)"
echo "AES_KEY=$(openssl rand -base64 32)"
echo "CREON_GATEWAY_API_KEY=$(openssl rand -hex 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
echo ""
echo "# 위 값을 운영 .env 또는 Docker Secrets 에 주입"
echo "# 절대 git/Slack/이메일에 평문 공유 금지"
```

---

## 3. 운영 배포 절차

### 3.1 신규 배포 (최초 운영 진입)

1. `cp .env.example .env`
2. §2.1 명령으로 모든 시크릿 생성, `.env` 에 채워넣기
3. `chmod 600 .env` (호스트에서 root 외 읽기 금지)
4. `APP_ENV=production` 설정
5. `CORS_ORIGINS` 에 정식 도메인만 (와일드카드 금지)
6. `DATABASE_URL`/`REDIS_URL` 의 호스트를 운영 IP/도메인으로 변경
7. §1.2 수동 검증 실행
8. `docker compose -f docker-compose.prod.yml up -d`
9. 백엔드 로그에서 `[SECURITY]` 메시지 없는지 확인

### 3.2 시크릿 변경 배포 (1회성 회전)

1. 새 시크릿 생성 (§2.1)
2. 메인터넌스 모드 ON (선택 — `JWT_SECRET` 변경 시 모든 세션 폐기되므로 사용자 안내)
3. `.env` 수정 → `docker compose restart backend worker scheduler`
4. 헬스 체크 (`/api/v1/health/ready`)
5. 메인터넌스 모드 OFF
6. 사용자 통지 (JWT 회전 시 강제 재로그인 안내)

---

## 4. 회전 주기 캘린더

`73_secrets_policy.md` §4 의 정책을 운영 캘린더로 변환한 표.
**PM 이 분기 1회 점검하며, DevOps 가 회전 D-7 알림을 받는다.**

| 시크릿 | 회전 주기 | 다음 회전 D-7 알림 |
|---|---|---|
| `JWT_SECRET` | 90일 | 매 회전 30분 다운타임 가능 |
| `AES_KEY` | 1년 | 데이터 재암호화 스크립트 사전 리허설 필수 |
| `CREON_GATEWAY_API_KEY` | 180일 | 게이트웨이 + 본체 동시 갱신 (4.2절 참조) |
| `POSTGRES_PASSWORD` | 180일 | DB 무중단 변경 절차 (4.3절 참조) |
| GPG 백업 키 | 1년 | 30일 유예 기간 (구 키로 복호화 가능) |
| TLS 인증서 | 90일 (Let's Encrypt 자동) | acme.sh 갱신 로그 확인 |
| AWS IAM Access Key | 90일 | 새 키 발급 후 24시간 내 구 키 비활성 |

### 4.1 GPG 백업 키 회전 절차

```bash
# 1. 새 키페어 생성 (RSA 4096, 만료 1년)
gpg --full-generate-key
# Real name: TradePilot Backup 2027
# Email: ops@tradepilot.example.com
# Expire: 1y

# 2. 공개키 export → 백업 스크립트에 배포
gpg --armor --export ops@tradepilot.example.com > /etc/tradepilot/backup_pubkey_new.asc

# 3. 백업 스크립트의 GPG_RECIPIENT 변경
# infra/backup/backup_full.sh 의 GPG_RECIPIENT 변수 갱신

# 4. 신규 백업 1건 생성 후 복구 리허설 (staging 에서)
./infra/backup/backup_full.sh
./infra/backup/restore_full.sh <archive>

# 5. 구 키는 30일간 보관 (구 백업 복구용)
# 30일 경과 후 오프라인 archive 보관 (USB/금고)
```

### 4.2 CREON_GATEWAY_API_KEY 동기화 회전

본체와 Windows 호스트의 키를 **동시에** 갱신해야 한다.
짧은 불일치 윈도우 동안 발주 실패가 발생할 수 있으므로 장 마감 후 진행한다.

```bash
# 1. 새 키 생성
NEW_KEY=$(openssl rand -hex 32)

# 2. 장 마감 후(15:30 이후) Windows 호스트에서 게이트웨이 .env 갱신
#    Windows 호스트: C:\TradePilot\.env 의 CREON_GATEWAY_API_KEY 갱신
#    .\start-gateway.ps1  로 재기동

# 3. 본체 .env 의 CREON_GATEWAY_API_KEY 갱신
sed -i "s|^CREON_GATEWAY_API_KEY=.*|CREON_GATEWAY_API_KEY=${NEW_KEY}|" /opt/tradepilot/.env

# 4. 본체 재기동
docker compose restart backend worker

# 5. 헬스 체크
curl -s http://gateway:9100/healthz
curl -s -H "X-Gateway-Api-Key: $NEW_KEY" http://gateway:9100/system/status
```

### 4.3 POSTGRES_PASSWORD 회전 (무중단)

```bash
# 1. 새 비밀번호 생성
NEW_PW=$(openssl rand -hex 24)

# 2. DB 사용자 비밀번호 변경 (DBA 작업)
psql -U postgres -c "ALTER USER tradepilot WITH PASSWORD '${NEW_PW}';"

# 3. .env 갱신 후 백엔드 롤링 재기동 (워커 → API 순)
sed -i "s|tradepilot:[^@]*@|tradepilot:${NEW_PW}@|" /opt/tradepilot/.env
docker compose restart worker scheduler
docker compose restart backend
```

---

## 5. Docker Secrets / Vault 마이그레이션 가이드

> 정책 정의 및 코드 패턴은 `73_secrets_policy.md` §3 에 있다.
> 본 절은 **실제 마이그레이션 작업 시 운영자가 따르는 단계별 체크리스트** 만 다룬다.

### 5.1 Docker Swarm Secrets 도입 체크리스트 (1개월 목표)

- [ ] 운영 클러스터를 Swarm 모드로 초기화 (`docker swarm init`)
- [ ] 시크릿 8종 생성 (`docker secret create`)
  - [ ] `jwt_secret`, `aes_key`, `creon_gateway_api_key`
  - [ ] `postgres_password`, `smtp_password`, `telegram_bot_token`
  - [ ] `sentry_dsn` (선택)
- [ ] `docker-compose.prod.yml` 에 `secrets:` 섹션 + 서비스별 마운트 추가
- [ ] `backend/app/core/config.py` 에 `_read_secret_or_env()` 헬퍼 추가 (정책 §3.2 예시 코드)
- [ ] `.env` 의 해당 변수 제거 (이전 환경변수 fallback 만 남김)
- [ ] 스테이징 환경에서 1주 검증
- [ ] 운영 전환 + 구 `.env` 시크릿 항목 안전 폐기
- [ ] 회전 절차 갱신 (`docker secret rm` + `create` + `service update`)

### 5.2 HashiCorp Vault 도입 체크리스트 (분기 목표)

- [ ] Vault 서버 HA 구성 (3 노드, Raft Storage)
- [ ] TLS 인증서 발급, 사설 CA 검증
- [ ] Auth Method: AppRole (백엔드/워커별 RoleID 분리)
- [ ] Policy 작성 (`secret/data/tradepilot/prod/*` read-only)
- [ ] Vault Agent Sidecar 컨테이너 추가 (시크릿 fetch + template)
- [ ] DB Dynamic Secrets 활성화 (PostgreSQL connection)
  - [ ] DB credential rotation TTL: 1시간
- [ ] Audit Log 활성화 + 외부 SIEM 연동
- [ ] 1주간 dual-read (Vault + .env) 운영 후 .env 폐기

---

## 6. 시크릿 누출 시 긴급 대응 매뉴얼

> 정책 정의는 `73_secrets_policy.md` §5 참조.
> 본 절은 **즉시 실행 가능한 명령 순서** 만 제공.

### 6.1 공통 초기 대응 (모든 누출 공통, 누출 의심 즉시 5분 내)

1. **사고 채널 개설**: Slack `#incident-secret-leak-YYYYMMDD`
2. **상황 보고**: PM + DevLead 호출 (P0 에스컬레이션, 30_operations_runbook §3 트리)
3. **타임라인 기록 시작**: 누구/언제/무엇/어떻게 인지함

### 6.2 시크릿별 즉시 명령

#### A. `JWT_SECRET` 누출
```bash
# 1. 메인터넌스 모드 ON
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://backend:8000/api/v1/admin/maintenance/enable

# 2. 새 시크릿 생성 + 즉시 교체
NEW=$(openssl rand -hex 32)
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${NEW}|" /opt/tradepilot/.env

# 3. Redis 의 모든 refresh 토큰 폐기
redis-cli --scan --pattern 'refresh:*' | xargs -r redis-cli del
redis-cli --scan --pattern 'session:*' | xargs -r redis-cli del

# 4. 백엔드 재기동 (모든 인스턴스)
docker compose restart backend worker scheduler

# 5. 사용자 강제 재로그인 안내 (이메일/인앱)
# 6. 메인터넌스 모드 OFF
```

#### B. `AES_KEY` 누출
```bash
# 1. 메인터넌스 모드 ON + 자동매매 전체 OFF
psql -c "UPDATE users SET auto_trade_enabled=false;"

# 2. 새 키 생성
NEW=$(openssl rand -base64 32)

# 3. 데이터 재암호화 스크립트 (정책 §4.2 참조)
#    backend/app/scripts/rotate_aes_key.py 실행
#    OLD_AES_KEY + NEW_AES_KEY 환경변수 동시 주입
OLD_AES_KEY="$AES_KEY" NEW_AES_KEY="$NEW" \
  python -m app.scripts.rotate_aes_key

# 4. .env 갱신 + 백엔드 재기동
sed -i "s|^AES_KEY=.*|AES_KEY=${NEW}|" /opt/tradepilot/.env
docker compose restart backend worker

# 5. CREON 계좌 비밀번호 재입력 안내 (사용자별 인앱 알림)
```

#### C. `CREON_GATEWAY_API_KEY` 누출
```bash
# 1. 게이트웨이 즉시 격리 (네트워크 차단)
#    Windows 호스트에서 게이트웨이 프로세스 중지
#    .\stop-gateway.ps1

# 2. 자동매매 전체 OFF + 미체결 주문 일괄 취소
psql -c "UPDATE users SET auto_trade_enabled=false;"

# 3. 새 키 + 동시 갱신 (§4.2 절차)
# 4. 본체 + 게이트웨이 동시 재기동
# 5. 30분간 발주 모니터링
```

#### D. DB 비밀번호 누출
```bash
# 1. DB 사용자 비밀번호 즉시 변경 (DBA)
psql -U postgres -c "ALTER USER tradepilot WITH PASSWORD '$(openssl rand -hex 24)';"

# 2. 모든 백엔드 컨테이너 재기동 (구 연결 폐기)
docker compose restart backend worker scheduler

# 3. DB audit log 검토 — 비정상 쿼리/접속 IP 분석 (DBA 협업)
```

#### E. GPG 백업 키 누출
```bash
# 1. 새 키페어 생성 (§4.1)
# 2. 신규 백업부터 새 키 사용
# 3. 구 키로 암호화된 백업은 안전 위치로 이동
#    (외부에 노출되지 않은 오프라인 저장소)
# 4. 누출 키가 사용된 백업 파일이 외부에 노출된 적이 있는지 감사
```

### 6.3 24시간 내 — RCA 작성
- 누출 경로 (Git push? Slack? 직원 단말?)
- 영향 평가 (사용자/거래 영향 추정)
- 재발 방지 액션 (pre-commit hook, RBAC 조정, 교육)
- 양식: `qa/` 디렉토리 RCA 템플릿 또는 `72_security_checklist.md` §4.5

### 6.4 1주 내 — 사후 조치
- 외부 보고 (필요 시 — 금융감독 기관, 사용자 통지)
- 본 정책 갱신 (해당 누출 패턴 명시적 차단 추가)
- 외부 펜테스트 의뢰 검토

---

## 7. 자주 묻는 질문 (FAQ)

### Q1. 개발 환경에서도 `_validate_production_settings()` 가 실행되나요?
A. 아니오. `APP_ENV != "production"` 이면 검증을 건너뜁니다. 개발 placeholder 값이 그대로 사용됩니다.

### Q2. 스테이징에서 운영과 동일한 시크릿을 써도 되나요?
A. **절대 금지.** 정책 §2 (`73_secrets_policy.md`) 에 따라 환경 간 시크릿 공유는 누출과 동일 취급합니다.

### Q3. `.env` 가 실수로 커밋되었습니다.
A. 즉시 §6 절차 수행. `git rm --cached .env` + `git push` 만으로는 히스토리에 남으므로,
`git filter-repo` 로 히스토리 삭제 + 노출된 모든 시크릿 회전 + 영향 평가.

### Q4. 운영 기동 중 fail-fast 가 발생했습니다.
A. 로그의 `[SECURITY]` 블록 항목을 확인하세요. 각 항목별 조치:
- "JWT_SECRET 가 운영 부적합" → §2.1 명령으로 재생성
- "DATABASE_URL 에 개발용 호스트" → 운영 DB 호스트로 변경
- "CORS_ORIGINS 와일드카드" → 정식 도메인만 콤마 구분

### Q5. AES_KEY 회전 중 일부 사용자 데이터 재암호화가 실패하면?
A. 재암호화 스크립트는 트랜잭션 단위로 실행해야 합니다.
실패 시 구 키 + 신 키 dual-read 모드를 1주 운영하며 점진 마이그레이션 권장
(`backend/app/scripts/rotate_aes_key.py` 의 `--dual-read` 옵션 향후 추가 예정).

---

## 8. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-14 | BackendDev | 최초 작성 — SEC-001 GATE-2 보강 (운영 진입 검증 강화 + 시크릿 회전 절차) |
