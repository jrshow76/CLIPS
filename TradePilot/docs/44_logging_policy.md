# TradePilot 로깅 정책 및 민감 정보 자동 마스킹

> 문서 ID: 44_LOGGING_POLICY
> 버전: v1.0
> 작성자: BackendDev
> 검토자: DevLead, BackendSenior, QA
> 최종 수정일: 2026-05-14
> 관련 문서:
>  - 보안 리뷰: `security/70_security_review_report.md` (SEC-007, SEC-009)
>  - 시크릿 정책: `security/73_secrets_policy.md`
>  - 운영 런북: `docs/30_operations_runbook.md`

본 문서는 TradePilot 백엔드/게이트웨이 로깅의 정책, 자동 마스킹 동작, 운영 시
민감 정보 노출 방지 절차를 정의한다.

---

## 1. 로깅 원칙

### 1.1 4가지 핵심 원칙

1. **구조화 우선** — JSON 키-값 페어로 기록(`structlog`).
   `logger.info("user_login", user_id=42, ip=request.client.host)`
2. **민감 정보 절대 평문 금지** — 비밀번호/토큰/OTP/API Key/계좌번호 등.
   자동 마스킹 processor 가 1차 방어선(§2 참조).
3. **추적 가능성** — 모든 요청에 `trace_id` 바인딩, 분산 로그 조회 가능.
4. **레벨 분리** — DEBUG(개발)/INFO(운영 정상)/WARNING(경고)/ERROR(오류)/CRITICAL(즉시 알림).

### 1.2 절대 로깅 금지 항목

| 분류 | 예시 |
|---|---|
| 시크릿 | JWT_SECRET, AES_KEY, CREON_GATEWAY_API_KEY, DB 비밀번호 |
| 사용자 자격증명 | 비밀번호 평문, OTP 코드, 비밀번호 재설정 토큰 |
| 토큰 | JWT access/refresh 토큰 전체, OAuth 토큰 |
| 금융정보 | 계좌번호, 계좌 비밀번호, 카드번호, CVC |
| PII | 주민등록번호, 휴대전화번호 전체(끝 4자리만 OK) |
| 환경변수 dump | `os.environ` 전체 출력 |

---

## 2. 자동 마스킹 (SEC-009-FOLLOWUP)

`backend/app/core/logging.py` 의 `mask_sensitive_fields` structlog processor 가
로깅 직전 모든 페이로드를 자동 스캔하여 민감 정보를 `***MASKED***` 로 대체한다.

### 2.1 동작 개요

```python
# structlog 파이프라인 등록 위치
configure(processors=[
    merge_contextvars,
    add_log_level,
    TimeStamper,
    StackInfoRenderer,
    format_exc_info,
    mask_sensitive_fields,   # ← 렌더링 직전 마스킹
    JSONRenderer,             # 또는 ConsoleRenderer
])
```

- **순수 함수**: 원본 event_dict 를 mutate 하지 않고 새 dict 반환
- **재귀 순회**: dict / list / tuple 을 최대 깊이 5 까지 순회
- **성능 영향 < 5%**: 단순 키 매칭 + 얕은 정규식만 사용

### 2.2 마스킹 대상 키 목록 (부분 매칭, case-insensitive, `-`/`_` 정규화)

| 패턴 | 매칭 예시 |
|---|---|
| `password` | password, user_password, PASSWORD, Password |
| `passwd` | passwd |
| `pwd` | pwd, cert_pwd |
| `secret` | secret, app_secret, JWT_SECRET |
| `token` | access_token, refresh_token, reset_token, jwt_token |
| `otp` | otp, otp_code, otp_secret |
| `api_key` | api_key, apikey, X-API-KEY |
| `apikey` | apikey |
| `authorization` | authorization, Authorization, AUTHORIZATION |
| `private_key` | private_key, rsa_private_key |
| `gpg` | gpg, gpg_key, gpg_passphrase |
| `aes_key` | aes_key, AES_KEY |
| `aes` | aes_key, aes_iv |
| `creon_password` | creon_password |
| `cert_pw` | cert_pw, certificate_pw |
| `bank_account` | bank_account, bank_account_no |
| `ssn` | ssn (주민등록번호) |
| `credit_card` | credit_card, credit_card_number |

### 2.3 마스킹 제외 키 (의도적 평문 보존)

운영 디버깅 가시성을 위해 다음 키는 패턴에 매칭되더라도 평문 보존:

- `csrf_token` — CSRF 토큰은 보안 토큰이지만 인증 흐름 디버깅에 필수
- `trace_id` — 분산 추적 ID (단어 "trace" 포함이나 민감 X)
- `request_id` — 요청 ID

### 2.4 URL 쿼리 마스킹

문자열 값에 다음 쿼리 파라미터가 포함되면 해당 값만 마스킹:

```
token=eyJabc.def       →  token=***MASKED***
api_key=ak-12345       →  api_key=***MASKED***
access_token=AAAA      →  access_token=***MASKED***
password=hello&user=a  →  password=***MASKED***&user=a
```

대상 키: `token`, `api_key`, `apikey`, `password`, `access_token`,
`refresh_token`, `otp`, `secret`

이 동작은 `SEC-007` (WebSocket URL token 누출) 회귀 방지와 직접 연결된다.

### 2.5 마스킹 예시

```python
# 입력 event_dict
{
    "event": "auth.refresh",
    "user_id": 42,
    "request": {
        "headers": {
            "authorization": "Bearer eyJxxx",
            "user-agent": "Mozilla",
        },
        "url": "wss://api/ws?token=eyJaaa",
        "refresh_token": "rt-abc.def",
    },
    "csrf_token": "csrf-ok",
    "trace_id": "trace-xyz",
}

# 출력 (마스킹 적용)
{
    "event": "auth.refresh",
    "user_id": 42,
    "request": {
        "headers": {
            "authorization": "***MASKED***",
            "user-agent": "Mozilla",
        },
        "url": "wss://api/ws?token=***MASKED***",
        "refresh_token": "***MASKED***",
    },
    "csrf_token": "csrf-ok",            # 제외 키 — 평문 유지
    "trace_id": "trace-xyz",            # 제외 키 — 평문 유지
}
```

---

## 3. 추가 마스킹 키 등록 방법

새로운 민감 필드를 도입할 때는 자동 마스킹 대상에 등록한다.

### 3.1 코드 변경

`backend/app/core/logging.py` 의 `_SENSITIVE_KEY_PATTERNS` 튜플에 패턴 추가:

```python
_SENSITIVE_KEY_PATTERNS: tuple[str, ...] = (
    "password",
    ...
    "new_secret_field",   # ← 추가
)
```

**가이드라인**:
- 패턴은 **소문자, 언더스코어 형식**. (정규화로 케이스/하이픈은 자동 흡수)
- 너무 일반적인 단어(예: `id`, `key` 단독)는 오탐 위험으로 피한다.
- 부분 매칭이므로 짧을수록 강하다(`secret` 1단어로 `*_secret_*` 모두 매칭).

### 3.2 테스트 추가

`backend/tests/unit/test_log_masking.py` 의 `test_민감_키는_마스킹된다` 파라미터에
새 키 추가:

```python
@pytest.mark.parametrize("key", [
    ...
    "new_secret_field",
])
```

### 3.3 검토

- DevLead 가 PR 리뷰 시 마스킹 대상 적정성 확인
- 운영 로그 1주 모니터링 후 누락/오탐 점검

---

## 4. 운영 시 로그 조회 가이드

### 4.1 로그 위치

| 환경 | 위치 | 형식 |
|---|---|---|
| 개발 | stdout (Docker logs) | ConsoleRenderer (컬러) |
| 스테이징 | stdout → Promtail → Loki | JSON |
| 운영 | stdout → Promtail → Loki → S3 (90일 보관) | JSON |

### 4.2 일상 조회 (Loki / Grafana)

```bash
# 특정 trace_id 의 전체 흐름 조회
{app="tradepilot",service="backend"} |= "trace_id=abc-123"

# 특정 사용자의 인증 이벤트
{app="tradepilot"} | json | event=~"auth.*" | user_id="42"

# 최근 1시간 ERROR 이상
{app="tradepilot"} | json | level=~"error|critical"
```

### 4.3 보안 사고 대응 시 로그 조회

```bash
# SEC-009 마스킹 누락 의심 시: ***MASKED*** 누락된 민감 키 검색
{app="tradepilot"} |~ "(?i)(password|secret|token)\":\\s*\"(?!\\*\\*\\*MASKED)"
# ↑ "password": "***MASKED***" 가 아닌 평문이 있는지 검색

# 특정 IP 의 모든 요청
{app="tradepilot"} | json | client_ip="1.2.3.4"

# 비정상 인증 실패 다발
{app="tradepilot"} | json | event="auth.login_failed" | rate(5m) > 10
```

### 4.4 PII 처리 (사용자 개인정보 요청 시)

- 사용자가 자신의 로그 사본을 요청하는 경우 (GDPR/개인정보보호법):
  1. PM 승인 + 사용자 본인 인증
  2. `user_id` 또는 `email` 기준 30일치 로그 export
  3. 시크릿/타 사용자 정보 마스킹 추가 후 전달

- 사용자가 자신의 데이터 삭제를 요청하는 경우:
  1. DB user soft-delete + 30일 후 hard-delete
  2. 로그는 90일 보관 후 자동 삭제 (보관 기간 단축 요청 불가 — 회계/감사 의무)
  3. 로그 내 PII 는 자동 마스킹으로 최소화 상태

---

## 5. 회귀 방지 — CI / PR 체크리스트

### 5.1 코드 리뷰 시 검토 항목

- [ ] 새 로깅 호출에서 시크릿/토큰/OTP 를 키 이름으로 사용하지 않았는가?
  (예: `logger.info(..., my_secret_value=v)` 가 아니라 적절한 키 이름 사용)
- [ ] 로깅하는 객체에 `__repr__` 이 시크릿을 평문 출력하지 않는가?
- [ ] 외부 라이브러리(예: SQLAlchemy echo) 가 SQL 에 시크릿을 노출하지 않는가?

### 5.2 자동 점검 (CI)

- `tests/unit/test_log_masking.py` 가 PR 마다 실행 (`pytest backend/tests/unit/test_log_masking.py`)
- 신규 민감 키 추가 시 테스트 케이스 동시 추가 — 미추가 시 리뷰어가 차단

### 5.3 운영 모니터링

- 월 1회 로그 샘플링 — 마스킹 누락 패턴 grep (`§4.3` 쿼리)
- 분기 1회 외부 보안 감사 — 로그 시스템 접근 권한 검토

---

## 6. 알려진 제약 및 후속 작업

### 6.1 제약 사항

| # | 제약 | 사유 / 회피 |
|--:|---|---|
| 1 | 재귀 깊이 5 제한 | 무한 그래프 방어. 깊은 중첩이 필요한 케이스는 사전 평탄화 권장 |
| 2 | `set` / 기타 컬렉션 미지원 | log 페이로드에 일반적이지 않음. 필요 시 list 로 변환 후 전달 |
| 3 | 바이너리 값 미마스킹 | 텍스트 키 매칭만 수행. 바이너리(`bytes`) 값은 별도 처리 |
| 4 | 외부 라이브러리 로그 미차단 | uvicorn/sqlalchemy 등의 로그는 stdlib logging 경유. WARNING 으로 톤다운 |

### 6.2 후속 개선 (Optional, 1개월~)

- [ ] stdlib `logging` 도 마스킹 처리 (현재 structlog 경로만 처리)
- [ ] 마스킹 처리 통계 메트릭 노출 (마스킹 횟수 카운터)
- [ ] Sentry 이벤트에도 동일 마스킹 적용 (`before_send` hook)
- [ ] 정규식 마스킹 확장 (이메일 부분 마스킹, IP 익명화 옵션)

---

## 7. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-14 | BackendDev | 최초 작성 — SEC-009 GATE-4 자동 마스킹 processor + 단위 테스트 |
