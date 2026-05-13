# TradePilot 종합 보안 리뷰 리포트

> 문서 ID: 70_SECURITY_REVIEW_REPORT
> 버전: v1.0
> 작성자: QA (Security Review)
> 검토자: PM, DevLead, BackendSenior, DBA
> 최종 수정일: 2026-05-13
> 점검 대상: TradePilot Backend / CREON Gateway / Frontend / Infra / CI/CD
> 점검 기준: OWASP Top 10 (2021) + 매매 시스템 특화 위협

---

## 1. Executive Summary

### 1.1 위험도 분포

| 위험도 | 건수 | 비중 |
|---|---:|---:|
| Critical | 3 | 12% |
| High | 6 | 24% |
| Medium | 9 | 36% |
| Low | 7 | 28% |
| **합계** | **25** | **100%** |

### 1.2 핵심 결론

- 코드 베이스의 인증·암호화 기본기(bcrypt cost=12, AES-256-GCM, HMAC-SHA256 OTP, 멱등성)는 **건전함**.
- 그러나 **Critical 3건(JWT 시크릿 기본값 + 시크릿 약한 검증 부재 + Kill Switch LIVE 모드 게이트웨이 미호출)**은 운영 진입 전 반드시 조치 필요.
- 매매 시스템 특화 리스크(주문 변조/모드 가드/한도 race/Kill Switch SLA) 중 **Kill Switch SLA 5초 보장이 확인되지 않음**(SEC-003) — High 등급.
- 본 리뷰에서 즉시 자동수정한 항목 9건은 §6 참조.
- 운영 GO/NO-GO 판정: **NO-GO 잠정** — Critical 3건 + High 6건 모두 해소 후 GO.

### 1.3 즉시 조치 / 단기 / 중기 / 장기 분류

| 분류 | 기준 | 건수 | 대표 이슈 |
|---|---|---:|---|
| **즉시(D-0)** | 운영 진입 차단 | 3 | SEC-001, SEC-002, SEC-003 |
| **단기(1주)** | 베타/스테이지 진입 차단 | 6 | SEC-004 ~ SEC-009 |
| **중기(1개월)** | 운영 안정화 | 9 | SEC-010 ~ SEC-018 |
| **장기(분기)** | 보안 성숙도 향상 | 7 | SEC-019 ~ SEC-025 |

---

## 2. 점검 범위 및 방법

### 2.1 점검 대상

| 영역 | 디렉토리 | 점검 라인 수(추정) |
|---|---|---:|
| Backend FastAPI | `TradePilot/backend/app/` | ~25,000 |
| CREON Gateway | `TradePilot/creon-gateway/creon_gateway/` | ~2,500 |
| Frontend Next.js | `TradePilot/frontend/src/` | ~12,000 |
| Database 스키마/마이그레이션 | `TradePilot/database/` | ~1,500 |
| Infra (nginx/backup/letsencrypt) | `TradePilot/infra/` | ~3,000 |
| CI/CD 워크플로우 | `.github/workflows/tradepilot-*.yml` | ~1,000 |

### 2.2 점검 방법

1. **사전 정책 분석**: `docs/14_exception_policy.md`, `docs/15_trading_policy.md`, `docs/24_api_response_spec.md`, `docs/41_nginx_tls_guide.md`, `docs/42_backup_recovery_guide.md`, `qa/53_exception_matrix.md` 정독.
2. **OWASP Top 10 항목별 grep + 코드 정독**: A01~A10 카테고리별 핵심 파일 점검.
3. **매매 시스템 특화 점검**: 주문 페이로드/모드 가드/한도 race/Kill Switch SLA.
4. **자동 도구 도입 가이드**: bandit, pip-audit, npm audit, gitleaks, semgrep 룰 설계(`scripts/`).

---

## 3. 발견 이슈 카탈로그

> 모든 이슈는 SEC-### 형태의 ID로 추적된다. 후속 작업은 Jira/Notion에 동일 ID로 등록한다.

### 3.1 Critical (P0 / 운영 진입 차단)

#### SEC-001 — 운영 환경에서 약한 JWT/AES/Gateway API Key 기본값 허용
- **카테고리**: A02 Cryptographic Failures, A05 Security Misconfiguration
- **위험도**: Critical
- **영향**: 기본값 시크릿(`change-this-in-production-please-32bytes-min`, `base64-encoded-32byte-random-key`, `replace-with-long-random-string`)으로 운영 기동 시 임의 사용자가 JWT 위조 / AES 복호화 / 게이트웨이 무단 호출 가능. 즉, **모든 사용자 계정 탈취 + 자동 실거래 발주**까지 가능.
- **재현**: `.env`를 채우지 않고 `APP_ENV=production`으로 기동 → JWT 발급/검증 정상 동작 → 누구나 임의 sub로 토큰 위조.
- **위치**:
  - `backend/app/core/config.py:54` (`JWT_SECRET` 기본값)
  - `backend/app/core/config.py:60` (`AES_KEY` 기본값)
  - `backend/app/core/config.py:64` (`CREON_GATEWAY_API_KEY` 기본값)
- **자동수정**: ✅ 적용 — `_validate_production_settings()` 추가, `APP_ENV=production`에서 기본값/짧은 키/와일드카드 CORS 감지 시 `RuntimeError` fail-fast.
- **후속 작업**: SEC-001-FOLLOWUP — Docker Secrets 또는 HashiCorp Vault 도입 (`73_secrets_policy.md` §3 참조).

#### SEC-002 — Gateway API Key 평문 비교(타이밍 사이드채널)
- **카테고리**: A02 Cryptographic Failures
- **위험도**: Critical(매매 게이트웨이 직접 노출 시)
- **영향**: `==` 비교는 첫 일치하지 않는 바이트에서 즉시 반환 → 응답 시간 차이로 키 추측 가능. 실거래 게이트웨이가 사설망에 있더라도 내부자/측면 이동 공격에 취약.
- **위치**: `creon-gateway/creon_gateway/main.py:113-117`
- **자동수정**: ✅ 적용 — `hmac.compare_digest`로 상수시간 비교 + 키 미설정/placeholder 시 503 fail-fast.
- **후속 작업**: SEC-002-FOLLOWUP — 본체↔게이트웨이 mTLS 도입 검토(추가 방어 계층).

#### SEC-003 — Kill Switch가 LIVE 모드 미체결 주문을 게이트웨이에서 실제 취소하지 않음
- **카테고리**: A04 Insecure Design / 매매 시스템 특화
- **위험도**: Critical
- **영향**: `KillSwitchService.trigger`가 LIVE 모드에서도 **DB만 CANCELED로 마킹**하고 CREON 게이트웨이의 `cancel_order` 호출이 누락됨. 결과적으로 비상정지 후에도 실거래 주문이 증권사에서 체결될 수 있음. 정책 문서(`14_exception_policy.md` §8, `15_trading_policy.md` §5)와 정면 위배.
- **위치**: `backend/app/services/kill_switch_service.py:62-92`
- **재현**: LIVE 모드 미체결 주문 1건 보유 → `POST /api/v1/orders/liquidate-all` 호출 → DB는 CANCELED, CREON 측은 미취소 → 시장에서 체결 발생.
- **자동수정**: ❌ 미적용 — 게이트웨이 호출 추가는 트랜잭션·재시도 정책·부분 실패 처리 등 OrderService와 연동된 설계 변경이 필요. **수정 범위가 넓어 임의 수정 금지 원칙에 따라 BackendSenior 작업으로 분리.**
- **후속 작업**: SEC-003-FOLLOWUP — `KillSwitchService`에 `OrderRouter.cancel_order` 호출 + 실패 시 E0014/E0015 매핑 + 5초 SLA 회로차단기 도입. **운영 진입 전 머지 필수.**

---

### 3.2 High

#### SEC-004 — Refresh Token 회전(rotation) 미구현 + Replay 탐지 부재
- **카테고리**: A07 Identification & Auth Failures
- **위험도**: High
- **영향**: 탈취된 refresh 토큰을 무한 재사용 가능 + 정상 사용자가 재발급 시 새 access만 발급되고 기존 refresh는 그대로 유효. 토큰 도난 탐지 불가.
- **위치**: `backend/app/services/auth_service.py:145-163` (수정 전)
- **자동수정**: ✅ 부분 적용 — `refresh()`에서 알 수 없는 refresh 토큰이 들어오면 해당 사용자 전 세션 폐기(replay 탐지). 만료 검증 추가.
- **후속 작업**: SEC-004-FOLLOWUP — 매 refresh 시 새 refresh 토큰 발급 + 기존 세션 즉시 폐기(완전 회전). 클라이언트 인터셉터 동시 갱신 race 처리 포함.

#### SEC-005 — CORS 미스컨피그(와일드카드 가능 + allow_credentials=True 동시 사용 위험)
- **카테고리**: A05 Security Misconfiguration
- **위험도**: High
- **영향**: `CORS_ORIGINS=*`을 설정하면 `allow_credentials=True`와 동시 사용 시 모든 origin이 인증 정보 포함 요청 가능 → CSRF/세션 탈취. 표준 CORS 명세상 브라우저가 차단하지만, 잘못된 사용자 정의 처리 시 우회 가능.
- **위치**: `backend/app/main.py:108-128`, `backend/app/core/config.py:38`
- **자동수정**: ✅ 적용 — `_validate_production_settings()`에서 운영 환경 `CORS_ORIGINS=*` 차단.
- **후속 작업**: SEC-005-FOLLOWUP — `main.py`에서 origin이 빈 리스트일 때 fail-fast(현재는 빈 origin 통과 가능). 개발/운영 분기 명확화.

#### SEC-006 — JWT 알고리즘 변조(alg 변경) 방어 미흡
- **카테고리**: A02 Cryptographic Failures
- **위험도**: High
- **영향**: PyJWT는 기본적으로 `algorithms=[...]` 화이트리스트로 `alg=none` 차단하지만, 토큰 헤더의 알고리즘이 서버 설정과 다른 알고리즘(예: HS256↔RS256 혼동)일 경우 키 혼동 공격(Key Confusion) 가능성. 설정에서 `JWT_ALGORITHM='none'` 등 잘못 설정 시 차단 부재.
- **위치**: `backend/app/core/security.py:107-126` (수정 전)
- **자동수정**: ✅ 적용 — 알고리즘 화이트리스트(`HS256/HS384/HS512/RS256/RS384/RS512`) 강제 + 토큰 헤더의 `alg`와 서버 설정 정확 일치 검증 + `alg=none` 명시 거부.
- **후속 작업**: SEC-006-FOLLOWUP — RS256 마이그레이션(공개키/개인키 분리, 검증자에게 공개키만 배포) 검토.

#### SEC-007 — WebSocket 인증 토큰이 nginx 액세스 로그에 평문 기록
- **카테고리**: A09 Security Logging Failures / A02
- **위험도**: High
- **영향**: 클라이언트는 `wss://.../ws/market?token=<JWT>`로 연결. nginx 액세스 로그에 `$request_uri`가 그대로 기록되어 access_token 평문이 로그 시스템(Loki/S3/Promtail)에 영구 보관됨 → 로그 시스템 침해 시 모든 사용자 토큰 탈취.
- **위치**: `infra/nginx/nginx.conf:46-66`(수정 전), `backend/app/api/websocket/market_ws.py:42-46`
- **자동수정**: ✅ 적용 — nginx에 `map`으로 `?token=...` 파라미터 마스킹(`token=***`) 후 로그 기록.
- **후속 작업**: SEC-007-FOLLOWUP — 첫 메시지 인증(`type=auth`) 모드를 기본으로 하고 query token 모드는 deprecation 경고. 프론트 클라이언트도 동일 방식으로 전환.

#### SEC-008 — DB 에러 메시지가 클라이언트 응답에 노출(정보 누설)
- **카테고리**: A09 Security Logging Failures / A05
- **위험도**: High(컬럼명/제약명 누출)
- **영향**: `IntegrityError` 처리에서 `details: {db_error: str(exc.orig)[:200]}` 응답 → 컬럼명, 제약명, 타입 등 DB 내부 구조가 외부 노출. SQL 인젝션 후속 공격 단서 제공.
- **위치**: `backend/app/core/exceptions.py:189-197` (수정 전)
- **자동수정**: ✅ 적용 — 클라이언트 응답에서 `db_error` 제거(서버 로그에는 유지).
- **후속 작업**: SEC-008-FOLLOWUP — 모든 5xx/4xx 응답 details에 대한 화이트리스트 정책 수립(`24_api_response_spec.md` §10.2 보강).

#### SEC-009 — OTP/비밀번호 재설정 토큰 평문 로깅(개발 환경에 한정되지만 위험)
- **카테고리**: A09 Security Logging Failures
- **위험도**: High(개발/스테이징 → 운영 누출 시 Critical로 격상)
- **영향**: `is_dev`인 경우 OTP 코드와 비밀번호 재설정 토큰을 평문으로 로깅. 실수로 운영 환경의 `APP_ENV` 설정이 잘못되거나 dev/stg 로그가 운영 시스템과 혼합 저장될 경우 즉시 사용자 계정 탈취.
- **위치**: `backend/app/services/auth_service.py:204-212, 271-283` (수정 전)
- **자동수정**: ✅ 적용 — 평문 로깅 제거. dev/test 환경에서는 Redis 키(`otp:debug:*`, `pwreset:*`)에서만 디버깅 가능.
- **후속 작업**: SEC-009-FOLLOWUP — structlog processor에 비밀번호/토큰/OTP 자동 마스킹 필터 추가(`****`).

---

### 3.3 Medium

#### SEC-010 — 비밀번호 재설정 토큰 무 만료 후 즉시 폐기 미보장
- **카테고리**: A07
- **위험도**: Medium
- **영향**: Redis TTL(1시간)에 의존. 사용 후 즉시 `del` 처리되나 동시 요청 시 race condition으로 1회용 보장 약함.
- **위치**: `backend/app/services/auth_service.py:285-300`
- **권장**: `GETDEL` (Redis 6.2+) 사용으로 원자적 1회용 보장.

#### SEC-011 — Idempotency 키 충돌 검증이 race condition에 취약
- **카테고리**: A04 / 매매 시스템 특화
- **위험도**: Medium
- **영향**: `OrderService.create`는 Redis cached + DB 중복 검사를 병렬 호출. 동시 2개 요청이 동일 키로 들어오면 둘 다 DB row 생성 가능.
- **위치**: `backend/app/services/order_service.py:73-84`
- **권장**: Redis `SETNX`(`SET key value NX EX ttl`)로 발주 직전 락 확보. 또는 DB UNIQUE(`idempotency_key`, `user_id`) 제약으로 IntegrityError fallback.

#### SEC-012 — 한도 검사 race condition (TradeLimitService)
- **카테고리**: 매매 시스템 특화
- **위험도**: Medium
- **영향**: `check_pre_order` 결과와 실제 주문 INSERT 사이에 다른 요청이 동시에 통과하여 일일 한도 초과 가능.
- **위치**: `backend/app/services/trade_limit_service.py` (별도 점검 필요)
- **권장**: 사용자 단위 분산 락(Redis Redlock) 또는 PostgreSQL `SELECT ... FOR UPDATE` + `daily_buy_total` 컬럼 원자 증분.

#### SEC-013 — Rate Limit 미들웨어가 Redis 장애 시 fail-open
- **카테고리**: A05
- **위험도**: Medium
- **영향**: Redis 장애 시 RateLimit이 모두 통과(`(True, limit, ...)`) → 의도된 graceful degrade이나 인증 API 브루트포스 윈도우가 열림.
- **위치**: `backend/app/core/middleware.py:163-166`
- **권장**: nginx 단의 `zn_login` 5r/min은 IP 기반으로 항상 동작하므로 일부 방어 가능. 추가로 `auth/login`은 fail-closed 정책 별도 적용.

#### SEC-014 — 사용자 enumeration: 로그인 응답 메시지가 "이메일 또는 비밀번호" 통합 메시지지만, 신규가입 E0051은 "이미 가입된 이메일" 명시
- **카테고리**: A07
- **위험도**: Medium
- **영향**: `/auth/signup` 응답으로 이메일 존재 여부 추정 가능.
- **위치**: `backend/app/services/auth_service.py:67`
- **권장**: 가입 응답을 통합 처리(이메일 인증 메일 발송 후 인증 시 실제 처리) 또는 RateLimit 강화로 enumeration 비용 증가.

#### SEC-015 — localStorage 기반 JWT 저장(XSS 시 토큰 탈취)
- **카테고리**: 프론트엔드 특화 / A02
- **위험도**: Medium
- **영향**: XSS 발생 시 access/refresh 토큰 모두 탈취 가능. 코드 주석에도 위험성 명시되어 있음.
- **위치**: `frontend/src/lib/auth/session.ts`
- **권장**: BFF(Backend-For-Frontend) 도입 또는 백엔드가 Secure/HttpOnly/SameSite=Lax 쿠키로 발급. 본 작업은 백엔드/프론트 합동 작업으로 별도 ticket.

#### SEC-016 — CSP가 Report-Only이며 `unsafe-inline`/`unsafe-eval` 허용
- **카테고리**: A05 / Frontend
- **위험도**: Medium
- **영향**: XSS 발생 시 CSP가 차단하지 못하고 보고만 함.
- **위치**: `infra/nginx/conf.d/_security.conf` + `docs/41_nginx_tls_guide.md` §3.
- **권장**: Next.js 13+ nonce 기반 script-src로 전환 → `unsafe-inline` 제거 → Enforce 모드 전환 (정책 §3 절차).

#### SEC-017 — Docker 평문 시크릿(`.env`)
- **카테고리**: A05
- **위험도**: Medium
- **영향**: `.env`가 호스트 파일시스템에 평문 보관 → 백업/스냅샷에 시크릿 포함 위험.
- **위치**: `docker-compose.yml`, `docker-compose.prod.yml` (Docker Secrets 미사용)
- **권장**: Docker Swarm Secrets 또는 HashiCorp Vault 도입(`73_secrets_policy.md` §3).

#### SEC-018 — Postgres/Redis 호스트 포트 노출(개발 compose)
- **카테고리**: A05
- **위험도**: Medium(개발), Low(운영 — prod 오버레이에서 제거됨)
- **영향**: 개발 환경의 5432, 6379가 호스트 인터페이스에 바인딩 → 노트북이 공용 네트워크에 있을 시 외부 접근 가능.
- **위치**: `docker-compose.yml:44-45, 61-62`
- **권장**: 개발도 `127.0.0.1:5432:5432` 형태로 루프백 바인딩 권장.

---

### 3.4 Low

#### SEC-019 — `bcrypt rounds=12` 운영 워크로드에 따라 조정 검토
- **카테고리**: A02
- **영향**: 12라운드는 적정선이나 장기적으로 14~15로 상향 검토.

#### SEC-020 — `httpx.AsyncClient`에 `verify=True` 명시 부재(기본값은 True이므로 OK이나 명시 권장)
- **위치**: `backend/app/integrations/creon/client.py:51`

#### SEC-021 — `partitioner.py` raw SQL DDL이 f-string으로 구성(입력은 int/고정 schema이나 표면적 위험)
- **위치**: `backend/app/services/data_ingestion/partitioner.py:39-65`
- **권장**: schema 인자 검증(allowlist) 추가.

#### SEC-022 — `audit_logs` 라우터가 `total: None`으로 페이지 카운트 미반환(보안과 무관, 운영 가시성 개선)
- **위치**: `backend/app/api/v1/admin.py:329`

#### SEC-023 — `/docs` (OpenAPI) 운영 환경 노출
- **위치**: `backend/app/main.py:101`
- **현재**: `is_test`만 비활성화. 운영 환경에서 `/docs` 노출 → API 표면적 가시성 증가.
- **권장**: `is_production` 시에도 비활성 또는 admin 인증 게이트.

#### SEC-024 — JWT `iss`/`aud` 클레임 미사용
- **위치**: `backend/app/core/security.py:74-104`
- **권장**: `iss=tradepilot`, `aud=api` 추가 검증 → 다른 시스템에서 발급된 JWT 차단.

#### SEC-025 — backup 파일 `ALLOW_PLAINTEXT_BACKUP` 토글 가능(기본 false이나 설정 실수 가능성)
- **위치**: `infra/backup/backup_full.sh` 환경변수
- **권장**: 운영 환경에서 컨테이너 환경변수 검증 단계 추가(시작 시 plaintext=true면 즉시 종료).

---

## 4. 위험도 매트릭스 (영향 × 가능성)

```
            가능성: 높음          가능성: 중간          가능성: 낮음
영향: 치명  | SEC-001, SEC-002    | SEC-003             |
           | SEC-005             |                      |
영향: 큼   | SEC-004, SEC-007    | SEC-006, SEC-008     | SEC-009 (운영)
           |                      | SEC-010, SEC-011     |
영향: 보통 | SEC-013, SEC-014    | SEC-012, SEC-015     | SEC-016, SEC-017
           |                      | SEC-018             |
영향: 작음 | SEC-019             | SEC-020 ~ SEC-025    |
```

---

## 5. OWASP Top 10 매핑 요약

| OWASP 카테고리 | 발견 이슈 | 상태 |
|---|---|---|
| A01 Broken Access Control | (별도 발견 없음) X-Trade-Mode 가드 + IDOR 점검(`order.user_id != user.id`) 통과 | ✅ |
| A02 Cryptographic Failures | SEC-001, SEC-002, SEC-006, SEC-015, SEC-019, SEC-020 | ⚠ |
| A03 Injection | partitioner f-string DDL(SEC-021만 표면) — 사용 입력 없음 | ✅ |
| A04 Insecure Design | SEC-003, SEC-011, SEC-012 | ⚠ |
| A05 Security Misconfiguration | SEC-001, SEC-005, SEC-013, SEC-016, SEC-017, SEC-018, SEC-023 | ⚠ |
| A06 Vulnerable Components | CI에서 pip-audit/npm audit 동작 중. 별도 즉시 이슈 없음 | ✅ |
| A07 Identification & Auth | SEC-004, SEC-010, SEC-014 | ⚠ |
| A08 Software and Data Integrity | 멱등성 OK, 백업 SHA256 OK, CI 서명 미적용(SEC-025) | ✅ |
| A09 Security Logging | SEC-007, SEC-008, SEC-009 | ⚠ |
| A10 SSRF | naver fallback이 코드 미구현 → 현재 시점 위험 없음. 도입 시 URL 화이트리스트 필요 | ✅ |

---

## 6. 즉시 자동수정 적용 내역

| ID | 파일 | 변경 내용 |
|---|---|---|
| SEC-001 | `backend/app/core/config.py` | `_validate_production_settings()` 추가, 운영 환경에서 약한 시크릿/와일드카드 CORS/DB_ECHO=True 등 fail-fast |
| SEC-002 | `creon-gateway/creon_gateway/main.py` | `hmac.compare_digest`로 API key 상수시간 비교 + placeholder/짧은 키 503 차단 |
| SEC-004 | `backend/app/services/auth_service.py` | `refresh()` 시 알 수 없는 refresh 토큰 → replay 탐지 + 전 세션 폐기, 만료 검증 추가 |
| SEC-005 | `backend/app/core/config.py` | 운영 환경 CORS 와일드카드 차단 |
| SEC-006 | `backend/app/core/security.py` | JWT 알고리즘 화이트리스트 + 토큰 헤더 alg와 서버 설정 정확 일치 검증 + `alg=none` 명시 차단 |
| SEC-007 | `infra/nginx/nginx.conf` | 액세스 로그에서 `?token=...` 쿼리 파라미터 마스킹 |
| SEC-008 | `backend/app/core/exceptions.py` | `IntegrityError` 응답에서 DB 원본 메시지 제거 |
| SEC-009 (a) | `backend/app/services/auth_service.py` | OTP 평문 로깅 제거(dev/test에서만 Redis 보관) |
| SEC-009 (b) | `backend/app/services/auth_service.py` | 비밀번호 재설정 토큰 평문 로깅 제거 |

미수정(설계 변경 필요) 항목:
- **SEC-003** (Kill Switch 게이트웨이 호출): BackendSenior 작업으로 분리. **운영 진입 전 완료 필수.**
- **SEC-010 ~ SEC-025**: 후속 작업으로 분리(§3 각 항목의 후속 작업 ID 참조).

---

## 7. 매매 시스템 특화 점검 결과

### 7.1 주문 변조 방지
- 페이로드 검증: `OrderRequestBody`(게이트웨이) 및 `OrderCreateIn`(본체)에서 종목코드 정규식, qty>=1, side/order_type enum 강제. ✅
- 음수/오버플로우: Pydantic v2 검증으로 차단. ✅
- 권장: BackendSenior가 `OrderCreateIn`의 `price` 음수/`Decimal` 오버플로우 추가 점검.

### 7.2 모드 가드 (X-Trade-Mode)
- `require_trade_mode` 의존성에서 헤더값 vs `users.trade_mode` 비교 → E0006 정상 발동. ✅
- `ROLE_TRADER` 권한이 LIVE 요청 시 E0002 차단. ✅
- `qa/53_exception_matrix.md` §1 E0006 자동화 테스트 존재. ✅

### 7.3 한도 체크 race condition
- **SEC-012** 항목 — Medium. 후속 조치 필요.

### 7.4 Kill Switch SLA
- **SEC-003** — Critical. 즉시 조치 필요.

### 7.5 SIM→LIVE 전환 7단계 검증
- 별도 라우터(`api/v1/settings.py`) 미점검. 본 리뷰 범위 외이나 후속 점검 ID 발급: SEC-026-FOLLOWUP.

### 7.6 CREON 게이트웨이 인증
- API Key 단일 — SEC-002 자동수정으로 timing-safe 확보.
- mTLS 미도입 — SEC-002-FOLLOWUP로 추적.

### 7.7 Redis Pub/Sub 외부 노출
- 운영 compose에서 호스트 포트 미노출. ✅
- Redis ACL 미적용 — 권장(SEC-027-FOLLOWUP).

### 7.8 WebSocket 인증
- query token 누출 — SEC-007 자동수정.
- 첫 메시지 인증 fallback 정상 동작. ✅

---

## 8. 후속 작업 트래킹

| ID | 우선순위 | 담당 | 마감 |
|---|---|---|---|
| SEC-001-FOLLOWUP | High | DevOps | 1개월 (Vault/Secrets) |
| SEC-002-FOLLOWUP | Medium | BackendSenior | 분기 (mTLS) |
| SEC-003-FOLLOWUP | **Critical** | **BackendSenior** | **운영 진입 전** |
| SEC-004-FOLLOWUP | High | BackendSenior | 1주 |
| SEC-005-FOLLOWUP | Medium | DevLead | 1주 |
| SEC-006-FOLLOWUP | Low | BackendSenior | 분기 |
| SEC-007-FOLLOWUP | Medium | FrontendSenior + BackendSenior | 1개월 |
| SEC-008-FOLLOWUP | Low | DevLead | 1개월 |
| SEC-009-FOLLOWUP | Medium | BackendDev | 1주 |
| SEC-010 ~ SEC-018 | Medium | 각 영역 담당 | 1개월 |
| SEC-019 ~ SEC-025 | Low | 각 영역 담당 | 분기 |
| SEC-026-FOLLOWUP | Medium | QA | 1주 (SIM→LIVE 7단계 점검) |
| SEC-027-FOLLOWUP | Medium | DBA | 1개월 (Redis ACL) |

---

## 9. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-13 | QA (Security Review) | 최초 작성 — Critical 3, High 6, Medium 9, Low 7 발견. 자동수정 9건 적용 |
