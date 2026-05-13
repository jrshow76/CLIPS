# TradePilot 보안 체크리스트

> 문서 ID: 72_SECURITY_CHECKLIST
> 버전: v1.0
> 작성자: QA (Security Review)
> 검토자: PM, DevLead
> 최종 수정일: 2026-05-13

본 체크리스트는 **머지 전 / 배포 전 / 운영 점검 / 사고 대응** 4단계로 구성된다.
PR 리뷰어, 운영자, IR 담당자가 즉시 사용할 수 있도록 항목별 검증 명령을 포함한다.

---

## 1. 코드 리뷰 체크리스트 (머지 전 필수)

### 1.1 인증/권한
- [ ] 신규/수정 라우터에 `Depends(CurrentUser)` 또는 `Depends(require_role(...))` 명시
- [ ] 주문/모드 변경 라우터에 `TradeModeDep` 명시
- [ ] 멱등성이 필요한 POST에 `X-Idempotency-Key` 처리 추가
- [ ] 자원 조회 시 `obj.user_id == current_user.id` IDOR 점검
- [ ] 관리자 전용 API는 `ROLE_ADMIN` 또는 `ROLE_OPERATOR` 가드

### 1.2 입력 검증
- [ ] 모든 입력은 Pydantic 모델로 정의 (`extra="forbid"` 권장)
- [ ] 종목코드, qty, price는 정규식/범위 제약
- [ ] DB UPSERT/UPDATE 시 SQLAlchemy ORM 사용 (raw SQL 지양)
- [ ] f-string으로 SQL 구성 금지 (불가피하면 식별자 화이트리스트)

### 1.3 비밀/로깅
- [ ] 비밀번호, 토큰(JWT/refresh/OTP/reset), API Key 평문 로깅 금지
- [ ] `log.info(...)` 호출에 `code=`, `token=` 키 사용 금지
- [ ] `print()`, `console.log()`로 민감정보 출력 금지
- [ ] 새 환경변수 추가 시 `.env.example`에 placeholder만 기록

### 1.4 외부 호출
- [ ] HTTP 클라이언트는 `httpx.AsyncClient` 사용 + `verify=True` 명시
- [ ] 외부 URL 호출 시 화이트리스트 검증 (SSRF 방어)
- [ ] 타임아웃 명시 (기본 5초 이내)
- [ ] 재시도는 idempotent 호출에만, 지수 백오프

### 1.5 응답 본문
- [ ] 에러 응답 `details`에 스택 트레이스/내부 경로/DB 컬럼명 노출 금지
- [ ] 성공 응답에 비밀번호/토큰/내부 ID 노출 금지

### 1.6 의존성
- [ ] 새 라이브러리 추가 시 `pip-audit` / `npm audit` 통과 확인
- [ ] `pyproject.toml` 핀(`==X.Y.*`) 유지
- [ ] CVE 알림 받은 라이브러리는 PR 설명에 사유 명시

### 1.7 자동화 도구
```bash
# 머지 전 로컬 검증
bash TradePilot/security/scripts/bandit_scan.sh
bash TradePilot/security/scripts/safety_check.sh
bash TradePilot/security/scripts/npm_audit.sh
bash TradePilot/security/scripts/gitleaks_scan.sh
```

---

## 2. 배포 전 체크리스트 (릴리스 게이트)

### 2.1 시크릿
- [ ] `.env`에 placeholder 값 미사용 (`change-this-...`, `replace-with-...`)
- [ ] `JWT_SECRET` ≥ 32자, 랜덤 (`openssl rand -base64 48`)
- [ ] `AES_KEY` 32바이트 base64
- [ ] `CREON_GATEWAY_API_KEY` ≥ 32자, 랜덤
- [ ] `POSTGRES_PASSWORD` ≥ 16자, 랜덤
- [ ] `SMTP_PASSWORD` 운영 계정 비밀번호로 교체
- [ ] `.env` 파일 권한 `chmod 600`

### 2.2 설정
- [ ] `APP_ENV=production`
- [ ] `DB_ECHO=false`
- [ ] `CORS_ORIGINS=https://tradepilot.example.com` (와일드카드 금지)
- [ ] `JWT_ALGORITHM=HS256` (또는 RS256)
- [ ] `LOG_LEVEL=INFO` (DEBUG 금지)
- [ ] 운영 docker-compose는 `docker-compose.prod.yml` 오버레이 사용
- [ ] postgres/redis 호스트 포트 미노출 확인 (`docker compose ps`)

### 2.3 인증서/TLS
- [ ] Let's Encrypt 인증서 발급 완료, 만료까지 ≥ 60일
- [ ] `bash scripts/deploy/ssl-test.sh tradepilot.example.com` SSL Labs A+ 확인
- [ ] HSTS 헤더 정상 응답 (`curl -I` `Strict-Transport-Security`)
- [ ] CSP Report-Only 정책 활성

### 2.4 데이터/백업
- [ ] 풀백업 스크립트 정상 동작 (`bash infra/backup/backup_full.sh --dry-run` 확인)
- [ ] WAL 아카이빙 동작 확인 (`ls /var/backup/tradepilot/wal/ | wc -l`)
- [ ] 마지막 복구 리허설 통과 (지난 일요일 04:00)
- [ ] GPG 키 만료까지 ≥ 60일

### 2.5 매매 시스템 특화
- [ ] **Kill Switch가 LIVE 모드에서 게이트웨이 cancel_order 호출 (SEC-003 후속 작업 머지 확인)**
- [ ] X-Trade-Mode 가드 통합 테스트 통과 (`pytest tests/qa -k "trade_mode"`)
- [ ] 한도 검증 통합 테스트 통과 (`pytest tests/qa -k "trade_limits"`)
- [ ] 멱등성 통합 테스트 통과 (`pytest tests/qa -k "idempotency"`)

### 2.6 모니터링
- [ ] Sentry DSN 설정 (`SENTRY_DSN`)
- [ ] Prometheus 메트릭 노출 확인 (`/metrics` 사설망 응답)
- [ ] 로그 수집기(Loki/Promtail) 컨테이너 정상

### 2.7 회귀
- [ ] `qa/53_exception_matrix.md` P0 코드 100% 자동화 통과
- [ ] `qa/52_trading_policy_tests.md` 통과
- [ ] E2E 시나리오 통과 (`qa/e2e/`)

---

## 3. 운영 점검 체크리스트

### 3.1 일간 (5분)

```bash
# 1. 보안 알림 확인
redis-cli -u $REDIS_URL XREAD COUNT 50 STREAMS tp:security.alerts 0

# 2. 로그인 실패 카운트
psql -d tradepilot -c "
  SELECT count(*), event FROM tp_audit.audit_login
  WHERE created_at > now() - interval '1 day' AND result='FAIL'
  GROUP BY event;
"

# 3. Kill Switch 발동 이력
psql -d tradepilot -c "
  SELECT trigger_type, count(*) FROM tp_trade.kill_switch_log
  WHERE created_at > now() - interval '1 day'
  GROUP BY trigger_type;
"

# 4. nginx 4xx/5xx 비율
grep '"status":[45]' /var/log/nginx/access.log | wc -l
```

### 3.2 주간 (30분)

- [ ] CSP Report-Only 위반 보고 검토 (Enforce 전환 검토)
- [ ] `tp:backup.event` 채널의 일요일 리허설 결과 확인
- [ ] pip-audit / npm audit 결과 검토 (`tradepilot-security` 워크플로우)
- [ ] 사용자별 일일 한도 변경 이력 점검 (`audit_login` event=SETTINGS_CHANGED)
- [ ] 관리자 API 호출 이력 점검 (관리자 ≥ 2인 교차 점검)

### 3.3 월간 (2시간)

- [ ] **JWT_SECRET 회전 검토** (90일 주기 권장)
- [ ] DB 비밀번호 회전 검토 (180일 주기)
- [ ] AES_KEY 회전 검토 (1년)
- [ ] GPG 키 만료 점검
- [ ] AWS IAM 권한 검토 (백업 사용자 최소 권한 유지)
- [ ] CVE 알림 채널 점검 (구독 정상 동작)
- [ ] 침해 사고 대응 매뉴얼 갱신 검토

### 3.4 분기

- [ ] 보안 리뷰 (본 체크리스트 + 외부 점검 권장)
- [ ] 펜테스트 (외부 업체 또는 내부 Red Team)
- [ ] 백업/복구 전체 시나리오 리허설 (시나리오 1~5)
- [ ] DR 시나리오 리허설 (다른 리전 신규 호스트)

---

## 4. 사고 대응 매뉴얼 (IR Playbook)

### 4.1 사고 분류

| 레벨 | 정의 | 알림 채널 | 1차 대응자 |
|---|---|---|---|
| **SEV-1** | 자본 직접 영향 (계정 탈취, 무단 발주) | 인앱+이메일+SMS+전화 | PM + DevLead 즉시 |
| **SEV-2** | 데이터 노출, 부분 시스템 장애 | 인앱+이메일+SMS | DevLead 30분 내 |
| **SEV-3** | 단일 계정 영향, 운영 가능 | 인앱+이메일 | 운영 당직 1시간 내 |

### 4.2 SEV-1: 계정 탈취 의심 시 대응

```bash
# 1. 즉시 해당 사용자 전 세션 폐기
psql -d tradepilot -c "
  UPDATE tp_user.sessions SET revoked_at=now()
  WHERE user_id=(SELECT id FROM tp_user.users WHERE email='<email>');
"

# 2. 자동매매 OFF
psql -d tradepilot -c "
  UPDATE tp_user.users SET trade_mode='SIM', auto_trade_enabled=false
  WHERE email='<email>';
"

# 3. Kill Switch 발동 (LIVE 미체결 주문 취소)
curl -X POST https://tradepilot.example.com/api/v1/orders/liquidate-all \
  -H "Authorization: Bearer <admin_token>" \
  -H "X-Trade-Mode: LIVE" \
  -d '{"reason":"SEV-1 incident"}'

# 4. 감사 로그 보존
pg_dump -t tp_audit.audit_login -t tp_audit.audit_order_history -F c \
  -f /var/backup/tradepilot/incident_$(date +%Y%m%d_%H%M%S).dump

# 5. 사용자 통보 + 비밀번호 재설정 강제 + KYC 재인증 요구
```

### 4.3 SEV-1: 시크릿 누출 (JWT_SECRET / AES_KEY) 시 대응

```bash
# 1. 즉시 시스템 메인터넌스 모드 ON
curl -X POST https://tradepilot.example.com/api/v1/admin/system/maintenance \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"enabled":true,"message":"긴급 점검 중"}'

# 2. 새 시크릿 발급
NEW_JWT=$(openssl rand -base64 48)
NEW_AES=$(openssl rand -base64 32)
echo "JWT_SECRET=$NEW_JWT" >> /etc/tradepilot/.env.new
echo "AES_KEY=$NEW_AES"  >> /etc/tradepilot/.env.new

# 3. AES_KEY 변경 시: 기존 암호화 데이터(creon_password_encrypted) 마이그레이션 필요
#    - 구 키로 복호화 → 신 키로 재암호화 스크립트 실행
python3 -m app.scripts.rotate_aes_key --old-key=$OLD_AES --new-key=$NEW_AES

# 4. 모든 활성 세션 폐기
psql -d tradepilot -c "UPDATE tp_user.sessions SET revoked_at=now() WHERE revoked_at IS NULL;"

# 5. 컨테이너 재시작
docker compose up -d --force-recreate backend-api backend-worker backend-scheduler

# 6. 메인터넌스 OFF + 사용자 재로그인 안내 발송
```

### 4.4 SEV-1: CREON 무단 발주 의심 시 대응

```bash
# 1. 게이트웨이 즉시 격리 (네트워크 차단)
docker network disconnect tp-net tp-backend-api  # 임시
# 또는 게이트웨이 호스트의 방화벽 인바운드 차단

# 2. CREON 측에서 발생한 모든 주문 취소 (수동, 대신증권 HTS 직접)

# 3. 게이트웨이 API Key 즉시 회전
NEW_GW_KEY=$(openssl rand -hex 32)
# 본체 .env + 게이트웨이 .env 동시 갱신 후 양측 재시작

# 4. 게이트웨이 호스트 침해 분석 (Windows 이벤트 로그, 네트워크 패킷)

# 5. 영향받은 사용자 손실 산정 + 보상 검토
```

### 4.5 사후 분석 (RCA)

24시간 내 작성:
1. **사고 요약**: 발생 시각, 탐지 시각, 대응 완료 시각, 영향 범위
2. **타임라인**: 분 단위 액션 기록
3. **근본 원인**: 5 Why 분석
4. **재발 방지**: 단기(1주) + 중기(1개월) + 장기(분기) 액션
5. **교훈**: 본 체크리스트 / 위협 모델 갱신 항목

---

## 5. 보안 연락처

| 역할 | 연락처 | 비고 |
|---|---|---|
| 보안 책임자 (CSO 역할) | PM | 1차 에스컬레이션 |
| 기술 대응 (CTO 역할) | DevLead | 시스템 격리/복구 |
| 데이터 대응 | DBA | 백업/복구/감사 로그 |
| 외부 신고 | KISA(118), 금감원 | 개인정보/금융사고 시 |

---

## 6. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-13 | QA (Security Review) | 최초 작성 - 머지/배포/운영/IR 4단계 |
