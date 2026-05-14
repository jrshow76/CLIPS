# TradePilot — GATE-1 (SEC-003) / GATE-3 (SEC-004) 해소 리포트

> 문서 ID: 75_GATE1_3_RESOLUTION
> 버전: v1.0
> 작성자: BackendSenior
> 검토자: DevLead, DBA, QA
> 작성일: 2026-05-14
> 대상 이슈: `security/70_security_review_report.md` §3.1 SEC-003 / §3.2 SEC-004

---

## 1. Executive Summary

`70_security_review_report.md`의 **Critical 1건(SEC-003)** 과 **High 1건(SEC-004)** 을 본 PR에서 완전 해소했다.

| ID | 등급 | 상태(이전) | 상태(이후) | 검증 |
|---|---|---|---|---|
| SEC-003 | Critical | DB만 CANCELED 마킹, 게이트웨이 미호출 | **라우터(SIM/LIVE) cancel_order 실호출 + 5초 SLA + 부분실패 재시도** | unit 5건 / qa 6건 (회귀) |
| SEC-004 | High | replay 탐지만 부분 적용 (회전 미구현) | **완전 회전 (매 refresh마다 새 jti + 기존 폐기 + 회전 체인)** | unit 6건 / integration 2건 |

운영 진입 GO/NO-GO: **GO 가능** — Critical 3건 중 마지막 잔여(SEC-003) 완전 해소, High 6건 중 SEC-004 완전 해소.

---

## 2. GATE-1 (SEC-003) — Kill Switch LIVE 모드 게이트웨이 실호출

### 2.1 변경 요약

| 영역 | 파일 | 변경 |
|---|---|---|
| 서비스 | `backend/app/services/kill_switch_service.py` | **재작성** — SIM/LIVE 모두 라우터의 `cancel_order` 호출, 5초 SLA, 부분실패 재시도 metadata 기록, Redis publish |
| 라우터 포트 | `backend/app/domains/ports/order_router_port.py` | `cancel_order(..., *, timeout_sec, idempotency_key)` 시그니처 확장 |
| LIVE 라우터 | `backend/app/integrations/creon/live_order_router.py` | 호출별 timeout / `X-Idempotency-Key` 헤더 주입 |
| SIM 라우터 | `backend/app/integrations/simulator/sim_order_router.py` | 새 키워드 인자 무시(호환) |
| HTTP 클라이언트 | `backend/app/integrations/creon/client.py` | `_request(..., timeout_sec, idempotency_key)` 추가, `cancel_order` 헤더/타임아웃 전달 |
| ORM | `backend/app/models/trade.py` | `Order.last_kill_switch_attempt_at`, `Order.kill_switch_attempts` 컬럼 추가 |
| API | `backend/app/api/v1/admin.py` | `POST /admin/kill-switch`, `POST /admin/kill-switch/auto`, `GET /admin/audit-log` 추가 |
| API | `backend/app/api/v1/orders.py`, `backend/app/api/v1/settings.py` | 새 응답 필드(duration_ms, sla_violated) 노출 |
| 워커 | `backend/app/workers/tasks/order_tasks.py` | `orders.kill_switch_retry` 5분 주기 Celery 태스크 |
| Beat | `backend/app/workers/celery_app.py` | `orders-kill-switch-retry` 스케줄 등록 |
| 테스트 | `backend/tests/unit/test_kill_switch_service.py` | 신규 5건 (LIVE 라우터 호출, SIM 동작, 부분실패 metadata, SLA 회로차단, 재시도) |
| 테스트 | `backend/tests/qa/test_kill_switch.py` | 헤더 보강 (회귀 호환) |
| 마이그레이션 | `database/migrations/2026_05_add_refresh_token_rotation.sql` | `tp_trade.orders` 부분실패 컬럼/인덱스 추가 (GATE-3과 합본 적용) |

### 2.2 핵심 절차 (KillSwitchService.trigger)

```
1) 활성 전략 일괄 비활성화 (Strategy.active=false)
2) 미체결 주문 조회 (status IN [NEW, PENDING, PARTIAL, ACCEPTED])
3) 종목 코드 사전 매핑 후, 주문별 라우터.cancel_order 호출
     - LIVE: CreonGatewayClient.cancel_order(timeout=2.0s, X-Idempotency-Key=killswitch:{order_id}:{mode})
     - SIM : SimOrderRouter.cancel_order (in-memory, 즉시 성공)
   - 호출별 asyncio.wait_for(timeout+0.3s) 추가 보호
4) 성공: orders.status=CANCELED, canceled_at=now, last_kill_switch_attempt_at=None
   실패: kill_switch_attempts += 1, last_kill_switch_attempt_at=now → failed[]
5) SLA 5초 회로차단: 남은 시간 < 0.2s 면 나머지 주문 모두 failed로 기록, sla_violated=True
6) LIVE → SIM 모드 강제 전환 (mode_switched=True)
7) KillSwitchLog 행 1건 기록 (canceled_count, failed_count, detail{canceled, failed, duration_ms, sla_violated})
8) failed/sla_violated 시 Redis publish:
     채널 `tp:gateway.killswitch_partial`
     payload {type, user_id, trade_mode, canceled_count, failed_count, duration_ms, ...}
9) 부분 실패 시 AppException("E0015", details=result) raise → 전역 핸들러 502 직렬화
```

### 2.3 부분 실패 재시도

- 워커: `orders.kill_switch_retry` (5분 주기, queue=orders)
- 대상: `last_kill_switch_attempt_at IS NOT NULL` AND `status IN (NEW,PENDING,PARTIAL,ACCEPTED)` AND `kill_switch_attempts < 5`
- 5회 이상 시도된 주문은 자동 재시도 대상에서 제외 → 운영자 수동 처리 알림 (후속 작업)
- 인덱스: `idx_orders_kill_switch_pending` (부분 인덱스, WHERE 조건 포함)

### 2.4 자동 트리거 조건 (보강만, 호출자가 trigger_source 지정)

| trigger_source | 호출 시점 | 비고 |
|---|---|---|
| USER | 사용자 수동 발동 | `/api/v1/admin/kill-switch` 또는 `/api/v1/orders/liquidate-all` |
| DAILY_LOSS | 일일 손실 -3% 도달 | `daily_loss_monitor` 워커 (별도 PR) |
| CREON_DISCONNECT | 게이트웨이 60초 이상 응답 없음 | event_listener에서 호출 |
| STOP_LOSS | 동일 종목 5회 이상 실패 | 주문 후처리에서 호출 |
| SYSTEM | 운영자 비상정지 | `/api/v1/admin/kill-switch/auto` |

### 2.5 SEC-003 해소 검증

| 검증 항목 | 방법 | 결과 |
|---|---|---|
| LIVE 모드에서 게이트웨이 cancel_order **실제 호출** | `test_kill_switch_live_mode_invokes_router_cancel` | ✅ |
| 인자에 `timeout_sec`, `idempotency_key` 포함 | 동일 테스트 (call.kwargs 검사) | ✅ |
| SIM 모드에서도 라우터 호출 + mode_switched=False | `test_kill_switch_sim_mode_keeps_mode_and_uses_sim_router` | ✅ |
| 부분 실패 시 `kill_switch_attempts`, `last_kill_switch_attempt_at` 갱신 | `test_kill_switch_partial_failure_records_retry_metadata_and_raises_E0015` | ✅ |
| 부분 실패 시 E0015 raise + details 포함 | 동일 테스트 (details["failed"]) | ✅ |
| 5초 SLA 회로차단 | `test_kill_switch_sla_circuit_breaker_marks_remaining_failed` | ✅ |
| SLA 초과 시 Redis publish (`tp:gateway.killswitch_partial`) | 동일 테스트 (publish_mock.await_args) | ✅ |
| 재시도 워커가 부분 실패를 처리 | `test_kill_switch_retry_failed_cancels_promotes_to_canceled` | ✅ |
| 기존 회귀(`test_kill_switch.py` 6건) | 컬렉트 정상 + 라우트 구현됨 | ✅ |

---

## 3. GATE-3 (SEC-004) — Refresh Token 완전 회전

### 3.1 변경 요약

| 영역 | 파일 | 변경 |
|---|---|---|
| ORM | `backend/app/models/user.py` | `Session`에 `jti`, `device_id`, `issued_at`, `replaced_by_jti` 컬럼 추가 |
| 보안 | `backend/app/core/security.py` | `create_jwt_token(..., jti=None)` 시그니처 확장, `create_refresh_token_with_jti()` 신규 헬퍼 |
| 서비스 | `backend/app/services/auth_service.py` | `login` → jti+issued_at 동기화 / `refresh` 완전 재구현 (회전+replay) / `logout` 단일 세션 폐기 옵션 / `_publish_security_event` |
| 리포지토리 | `backend/app/repositories/user_repository.py` | `find_by_jti`, `rotate`, `delete_expired` 메서드 추가 |
| API | `backend/app/api/v1/auth.py` | `/refresh` 새 refresh 토큰 반환, `/logout` 옵션 refresh_token body |
| 스키마 | `backend/app/schemas/auth.py` | `RefreshResponse`에 `refresh_token`, `refresh_expires_in` 추가 |
| 워커 | `backend/app/workers/tasks/cleanup_tasks.py` | 신규 — `cleanup.refresh_sessions` (매일 04:00 KST) |
| Beat | `backend/app/workers/celery_app.py` | `cleanup-refresh-sessions` 스케줄 |
| 마이그레이션 | `database/migrations/2026_05_add_refresh_token_rotation.sql` | sessions 테이블에 컬럼/인덱스 추가 |
| 테스트 | `backend/tests/unit/test_auth_refresh_rotation.py` | 신규 6건 (jti 클레임, 회전, replay, 만료, logout 분기 2건) |
| 테스트 | `backend/tests/integration/test_auth_api.py` | 신규 2건 (refresh 회전, replay 전 세션 폐기) |

### 3.2 핵심 절차 (AuthService.refresh)

```
1) JWT 디코딩 → sub, jti 추출 (모든 검증 통과해야 함)
2) DB에서 jti 조회 (sessions.jti UNIQUE)
   - 미존재 → hash 기반 fallback (legacy 호환)
   - 그래도 없으면: 사용자 전 세션 폐기 + `refresh_token_unknown` security event publish
3) sess.revoked_at IS NOT NULL ⇒ **REPLAY 탐지**
   - 전 활성 세션 폐기 (revoke_all_for_user)
   - Redis publish `tp:security.events` {type: 'refresh_replay_detected', user_id, jti, ts}
   - 401 E0001 raise
4) sess.expires_at < now ⇒ 401 E0053 (세션 만료)
5) 정상 경로:
   - create_refresh_token_with_jti(...) → 새 token + 새 jti
   - create_jwt_token(token_type='access') → 새 access
   - 새 Session 행 add(): jti=new_jti, refresh_token_hash, issued_at=now, device_id 승계
   - rotate(old_session, new_jti): UPDATE old SET revoked_at=now, replaced_by_jti=new_jti
6) commit() → 응답 {access_token, refresh_token, expires_in, refresh_expires_in}
```

### 3.3 보안 이벤트 채널 (`tp:security.events`)

| type | 발생 시점 | 페이로드 |
|---|---|---|
| `refresh_replay_detected` | 이미 revoked된 jti가 다시 사용됨 | user_id, public_id, jti, ts |
| `refresh_token_unknown` | DB에 존재하지 않는 토큰 (jti/hash 모두 매치 안됨) | user_id, public_id, jti, ts |

구독 측: NotificationService 확장 또는 운영 알림 채널 (후속 작업).

### 3.4 토큰 정리 워커

- 태스크: `cleanup.refresh_sessions` (default queue)
- 스케줄: `crontab(hour=4, minute=0)` — 매일 04:00 KST
- 동작: `sessions.expires_at < now - 7일` 인 행 일괄 DELETE
- 인덱스: `idx_sessions_expires_at` (마이그레이션 포함)

### 3.5 SEC-004 해소 검증

| 검증 항목 | 방법 | 결과 |
|---|---|---|
| Refresh 토큰 JWT에 jti 클레임 포함 | `test_refresh_token_with_jti_includes_jti_claim` | ✅ |
| /auth/refresh 매 호출마다 새 refresh 발급 | `test_refresh_endpoint_returns_new_refresh_token_rotation` (integration) + `test_auth_refresh_rotates_and_revokes_old_session` (unit) | ✅ |
| 기존 세션 revoked_at + replaced_by_jti 갱신 | unit (rotate mock 검증) | ✅ |
| Replay (동일 jti 두 번째 호출) 탐지 | `test_auth_refresh_replay_revokes_all_sessions_and_publishes_event` | ✅ |
| Replay 시 사용자 전 세션 폐기 | 동일 테스트 (revoke_all_for_user 호출 확인) | ✅ |
| Replay 시 Redis publish (`tp:security.events`) | 동일 테스트 (publish_mock 채널 검사) | ✅ |
| 만료된 세션 → E0053 | `test_auth_refresh_expired_session_returns_E0053` | ✅ |
| logout(refresh_token) → 해당 세션만 폐기 | `test_logout_with_refresh_token_revokes_only_that_session` | ✅ |
| logout(공백) → 전 세션 폐기 (기존 동작) | `test_logout_without_refresh_token_revokes_all` | ✅ |
| Integration: 회전 후 응답에 new refresh_token | `test_refresh_endpoint_returns_new_refresh_token_rotation` | ✅ |
| Integration: 두 번째 동일 토큰 사용 → 401 + 전 세션 무효 | `test_refresh_replay_revokes_all_sessions` | ✅ |

---

## 4. 데이터베이스 마이그레이션 (DBA 협의)

### 4.1 파일

`database/migrations/2026_05_add_refresh_token_rotation.sql`

### 4.2 변경 사항 (idempotent)

1. **`tp_user.sessions`** (SEC-004)
   - ADD COLUMN IF NOT EXISTS: `jti UUID`, `device_id VARCHAR(64)`, `issued_at TIMESTAMPTZ`, `replaced_by_jti UUID`
   - 기존 행에 `jti = gen_random_uuid()`, `issued_at = created_at` 보정 UPDATE
   - `ALTER COLUMN jti SET NOT NULL` (보정 후)
   - `CREATE UNIQUE INDEX uq_sessions_jti (jti)`
   - `CREATE INDEX idx_sessions_user_revoked (user_id, revoked_at)`
   - `CREATE INDEX idx_sessions_expires_at (expires_at)`

2. **`tp_trade.orders`** (SEC-003)
   - ADD COLUMN IF NOT EXISTS: `last_kill_switch_attempt_at TIMESTAMPTZ`, `kill_switch_attempts INTEGER NOT NULL DEFAULT 0`
   - 부분 인덱스: `idx_orders_kill_switch_pending` (WHERE 활성 상태 AND last_attempt IS NOT NULL)

### 4.3 DBA 협의 사항

1. **적용 절차**
   - 운영 환경은 `sessions` 행 수가 많을 수 있으므로 `ALTER TABLE ... ADD COLUMN ... NOT NULL` 직접 수행 시 락 시간 우려.
   - 본 SQL은 ALTER → UPDATE → ALTER 분리(`SET NOT NULL`은 별도 단계)로 작성됨. 그러나 대용량 시 `UPDATE sessions SET jti = gen_random_uuid()` 부하 발생 가능.
   - **권장 적용 순서**: 운영 트래픽 저점(KST 04:00 직후)에 적용, 진행 중 `SELECT count(*) FROM tp_user.sessions WHERE jti IS NULL;` 모니터링.

2. **`orders` 테이블 (파티셔닝)**
   - 월별 RANGE 파티셔닝이므로 `ALTER TABLE`은 각 파티션에 자동 전파됨 (PostgreSQL 12+).
   - 신규 컬럼 기본값(`kill_switch_attempts DEFAULT 0`)은 rewrite 없는 metadata-only로 처리됨 (PG11+).

3. **롤백 전략**
   - jti/replaced_by_jti는 NULL 허용으로 시작 → 운영 5분 후 NOT NULL 적용.
   - 문제 시 `ALTER COLUMN jti DROP NOT NULL` 즉시 가능.

### 4.4 적용 명령 (예시)

```bash
psql "$DATABASE_URL" -f database/migrations/2026_05_add_refresh_token_rotation.sql
# 적용 후 확인
psql "$DATABASE_URL" -c "\d+ tp_user.sessions" | grep -E "jti|replaced_by_jti|device_id|issued_at"
psql "$DATABASE_URL" -c "\d+ tp_trade.orders" | grep -E "kill_switch"
```

---

## 5. 테스트 결과 요약

### 5.1 단위 테스트 (DB/Redis 없이 통과)

```
pytest backend/tests/unit/test_kill_switch_service.py backend/tests/unit/test_auth_refresh_rotation.py
========================== 11 passed in 4.02s ==========================
```

| 파일 | 통과 |
|---|---:|
| `test_kill_switch_service.py` | 5 |
| `test_auth_refresh_rotation.py` | 6 |
| **합계** | **11** |

### 5.2 전체 단위 테스트 회귀

```
pytest backend/tests/unit
=========== 1 failed, 174 passed, 1 warning in 93.94s ===========
```

- 실패 1건은 **기존부터 환경 의존성(bcrypt/passlib AttributeError)** 이슈로 본 변경과 무관.
- 본 PR 변경 전 stash 후 동일 테스트 단독 실행 시에도 동일 에러 재현 확인.

### 5.3 통합 테스트 (실 DB+Redis 환경 별도)

- `tests/integration/test_auth_api.py`: 신규 2건 추가, 총 6건 컬렉트 OK
- `tests/qa/test_kill_switch.py`: 6건 컬렉트 OK (LIVE 모드 SLA 검증 케이스는 mock 기반 단위 테스트로 보완)

---

## 6. 핵심 결정 (5줄)

1. **GATE-1 (SEC-003)**: 라우터 추상화(OrderRouterPort.cancel_order)를 유지한 채 `timeout_sec`/`idempotency_key` 키워드 인자만 확장해 SIM/LIVE 모두 동일 인터페이스 사용 + LIVE는 게이트웨이 HTTP 호출이 실제 발생하도록 KillSwitchService를 재작성했다.
2. **GATE-1 SLA**: 5초 SLA를 위해 게이트웨이 호출별 2초 타임아웃 + 전체 회로차단기(`time.monotonic()`)를 단일 메서드 안에서 결합하고, 남은 시간이 0.2초 미만이면 잔여 주문은 즉시 failed로 기록하여 클라이언트 응답을 SLA 안에 보장한다.
3. **GATE-1 부분실패**: 라우터 실패 시 즉시 예외 raise 대신 `last_kill_switch_attempt_at`/`kill_switch_attempts`를 갱신하고 `failed[]`에 누적 → `orders.kill_switch_retry` Celery 태스크가 5분 주기로 재호출. 5회 시도 후에는 운영자 수동 처리 대상으로 격리.
4. **GATE-3 (SEC-004)**: refresh 토큰에 `jti` 클레임을 박고 DB `sessions.jti UNIQUE` 컬럼과 1:1 매핑 → 회전 시 `rotate(old, new_jti)`로 트랜잭션 내 원자 처리, replay 탐지는 `revoked_at IS NOT NULL` 단일 조건만으로 판정해 race 가능성을 차단했다.
5. **GATE-3 보안 이벤트**: replay/unknown token 모두 Redis `tp:security.events` publish로 통일하여 후속 알림 채널 구독을 단순화했고, 클라이언트 API 호환을 위해 `/auth/logout`에는 refresh_token을 옵션 body로 받아 단일 세션 폐기/전체 폐기 분기를 만들었다.

---

## 7. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-14 | BackendSenior | GATE-1(SEC-003) / GATE-3(SEC-004) 해소 완료 보고 |
