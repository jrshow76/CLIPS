# TradePilot CREON 통합 테스트 케이스

> 문서 ID: 61_CREON_INTEGRATION_CASES
> 버전: v1.0
> 작성자: BackendSenior, QA
> 검토자: DevLead, PM
> 최종 수정일: 2026-05-12

본 문서는 `60_creon_integration_plan.md` 의 Stage 1 ~ Stage 4 단계에서 실행하는 통합 테스트 케이스를 정의한다. 총 **48건**의 케이스를 포함하며, 각 케이스는 사전조건/실행순서/검증포인트/예상결과/우선순위(P0~P2)/자동화 가능 여부를 명시한다.

표기:
- **P0**: 통과 필수 (롤백 트리거)
- **P1**: 통과 강력 권고 (1건 이내 실패 허용, 차주 fix)
- **P2**: 모니터링 목적 (실패 시 이슈 등록만)
- **자동화**: 자동(`AUTO`) / 반자동(`SEMI`) / 수동(`MANUAL`)

---

## 1. 카테고리: 연결 / 인증 (TC-INT-001 ~ 008)

### TC-INT-001 — CREON Plus 미로그인 상태 검출 [P0, SEMI]
- **사전조건**: Windows 호스트, CREON Plus 미로그인.
- **실행순서**:
  1. 게이트웨이 기동 (`start-gateway.ps1 -NoLogin`).
  2. `GET /readyz` 호출.
- **검증포인트**: 응답 `com_connected=false`, `account_loaded=false`.
- **예상결과**: HTTP 200, ok=false.

### TC-INT-002 — CREON Plus 로그인 후 정상 readyz [P0, SEMI]
- **사전조건**: CREON Plus 로그인 + 매매 비밀번호 입력 완료.
- **실행순서**: 게이트웨이 재기동 후 `GET /readyz`.
- **검증**: `ok=true, com_connected=true, account_loaded=true, trade_env=SIM`.

### TC-INT-003 — 잘못된 API Key 거부 [P0, AUTO]
- **사전조건**: 게이트웨이 정상 기동.
- **실행순서**: 잘못된 `X-Gateway-Api-Key` 로 `GET /system/status` 호출.
- **검증**: HTTP 401, detail "invalid api key".

### TC-INT-004 — 정상 API Key 통과 [P0, AUTO]
- **사전조건**: 정상 API Key.
- **검증**: `success=true`, `data.connected=true`.

### TC-INT-005 — CREON 단절 후 자동 재연결 [P0, MANUAL]
- **사전조건**: Stage 1 정상 기동.
- **실행순서**:
  1. CREON Plus 종료.
  2. 5초 대기 후 `GET /readyz` (com_connected=false 확인).
  3. CREON Plus 재기동.
  4. 30초 이내 헬스비트 정상 복귀 확인.
- **검증**: `_reconnect_failures` 카운터 리셋, 헬스비트 재수신.

### TC-INT-006 — 재연결 3회 실패 시 CRITICAL 알림 [P0, MANUAL]
- **사전조건**: CREON Plus 종료 후 즉시 재기동 불가 상황.
- **실행순서**: 게이트웨이가 3회 재연결 시도 → 모두 실패.
- **검증**: `tp:gateway.alert` 채널에 level=CRITICAL, code=G0002 발행.

### TC-INT-007 — 게이트웨이 단절 시 본체 LIVE→SIM 강제 [P0, AUTO]
- **사전조건**: 본체 LIVE 모드 사용자, 게이트웨이 헬스비트 15초 이상 미수신.
- **실행순서**: 게이트웨이 강제 종료 후 15초 대기.
- **검증**: 본체 `users.trade_mode = SIM` 자동 변경, 알림 발송.

### TC-INT-008 — 멱등성 키 유효기간 [P1, AUTO]
- **사전조건**: 동일 idempotency_key 로 주문 2회.
- **검증**: 두 번째 호출은 캐시된 응답 반환, broker_order_no 동일.

---

## 2. 카테고리: 계좌 / SIM-REAL 분기 (TC-INT-010 ~ 015)

### TC-INT-010 — SIM 모드에서 SIM 접두사 계좌 반환 [P0, AUTO]
- **사전조건**: `CREON_TRADE_ENV=SIM, CREON_ACCOUNT_PREFIX_SIM=55`.
- **실행순서**: `GET /account`.
- **검증**: 모든 계좌 번호가 `55` 로 시작.

### TC-INT-011 — REAL 모드에서 REAL 접두사 계좌 반환 [P0, AUTO]
- **사전조건**: `CREON_TRADE_ENV=REAL`. (테스트는 mock으로 검증)
- **검증**: 모든 계좌 번호가 `CREON_ACCOUNT_PREFIX_REAL` 로 시작.

### TC-INT-012 — SIM 모드 명시 안 됨 시 디폴트 SIM [P0, AUTO]
- **사전조건**: `CREON_TRADE_ENV` 미설정.
- **검증**: 기본값 SIM 적용. (`settings.is_sim_mode() == True`)

### TC-INT-013 — 잘못된 모드 값 거부 [P1, AUTO]
- **사전조건**: `CREON_TRADE_ENV=DEV` 설정 시도.
- **검증**: pydantic Literal 검증으로 기동 실패.

### TC-INT-014 — 잔고 조회 (모의투자) [P0, SEMI]
- **사전조건**: SIM, 모의투자 입금 1억원.
- **실행순서**: `GET /account/balance`.
- **검증**: `cash` ≈ 1억원, `trade_env=SIM`.

### TC-INT-015 — 보유 종목 조회 (모의투자) [P0, SEMI]
- **사전조건**: 모의투자에서 005930 10주 보유.
- **실행순서**: `GET /account/positions`.
- **검증**: 응답에 005930 종목 포함, qty=10.

---

## 3. 카테고리: 주문 (매수/매도/취소) (TC-INT-020 ~ 035)

### TC-INT-020 — 모의투자 지정가 매수 (005930) [P0, SEMI]
- **사전조건**: SIM, 잔고 충분, 현재가 조회 가능.
- **실행순서**:
  1. `GET /market/quote/005930` 으로 현재가 P 조회.
  2. `POST /orders` (side=BUY, qty=1, order_type=LIMIT, price=P).
  3. 5초 내 `tp:account.execution` 메시지 수신.
- **검증**: HTTP 200, accepted=true, broker_order_no 비어있지 않음. 체결 메시지에 동일 broker_order_no.

### TC-INT-021 — 모의투자 시장가 매수 [P0, SEMI]
- **사전조건**: SIM, 정규장 시간.
- **검증**: 즉시 체결, 평균 지연 < 800ms.

### TC-INT-022 — 모의투자 지정가 매도 [P0, SEMI]
- **사전조건**: 005930 1주 이상 보유.
- **검증**: 매도 체결, 잔고 -1, 예수금 +체결가.

### TC-INT-023 — 시장가 매도 [P0, SEMI]
- **검증**: 즉시 체결, 잔고 갱신.

### TC-INT-024 — 미체결 주문 취소 [P0, SEMI]
- **사전조건**: 현재가 - 5% 가격으로 지정가 매수 (체결 안 됨).
- **실행순서**: `POST /orders/{id}/cancel`.
- **검증**: canceled=true, 미체결 목록에서 사라짐.

### TC-INT-025 — 잔고 부족 매수 거부 [P0, AUTO]
- **사전조건**: 잔고 1만원, 1000만원 주문 시도.
- **검증**: HTTP 200, success=false, error.code=G0011, raw_code=-307.

### TC-INT-026 — 매도 수량 부족 거부 [P0, AUTO]
- **사전조건**: 005930 미보유, 매도 시도.
- **검증**: error.code=G0011, raw_code=-308.

### TC-INT-027 — 잘못된 종목코드 거부 [P0, AUTO]
- **사전조건**: code="ABCDEF".
- **검증**: HTTP 422 (pydantic) 또는 G0010.

### TC-INT-028 — qty=0 거부 [P0, AUTO]
- **검증**: HTTP 422 (pydantic ge=1).

### TC-INT-029 — LIMIT 주문 price 누락 거부 [P0, AUTO]
- **사전조건**: order_type=LIMIT, price=null.
- **검증**: HTTP 200, success=false, error.code=G0012.

### TC-INT-030 — 멱등성: 동일 키 2회 발주 [P0, AUTO]
- **사전조건**: idempotency_key="test-001".
- **실행순서**: 동일 키로 2회 호출.
- **검증**: 두 응답이 완전히 동일 (broker_order_no 동일), 실제 발주는 1회.

### TC-INT-031 — 100건 연속 주문 (요청 제한 안정성) [P0, AUTO]
- **사전조건**: SIM 환경.
- **실행순서**: 1초 간격 없이 100건 발주.
- **검증**: 100건 모두 accepted=true, 게이트웨이가 자동 페이싱하여 CREON 제한 위반 0건.

### TC-INT-032 — 평균 체결 지연 측정 [P0, AUTO]
- **사전조건**: 100건 주문 발주 + 체결 시간 기록.
- **검증**: 평균 < 800ms, 95th < 1500ms.

### TC-INT-033 — 정정 주문 (가격 변경) [P2, MANUAL] — v1.1 범위
- 본 항목은 v1.0 범위 외이며 v1.1 회귀에서 수행.

### TC-INT-034 — 상하한가 도달 주문 거부 [P1, MANUAL]
- **사전조건**: 상한가 도달한 종목.
- **검증**: error.code=G0013 (상하한가 도달), raw_code=-311.

### TC-INT-035 — 거래 정지 종목 주문 거부 [P1, MANUAL]
- **사전조건**: 거래 정지 종목.
- **검증**: error.code=G0014, raw_code=-312.

---

## 4. 카테고리: 시세 / 실시간 (TC-INT-040 ~ 045)

### TC-INT-040 — 현재가 조회 [P0, SEMI]
- **검증**: 005930 가격이 NAVER/Daum 시세와 ±0.5% 이내 일치.

### TC-INT-041 — 종목 마스터 조회 [P0, SEMI]
- **검증**: 005930 → "삼성전자", KOSPI.

### TC-INT-042 — 호가 10단계 조회 [P0, AUTO]
- **검증**: bids 10건 + asks 10건, 가격이 단조 증가/감소.

### TC-INT-043 — 실시간 시세 구독 [P0, SEMI]
- **사전조건**: `POST /subscribe/quote {codes: ["005930"]}`.
- **검증**: 5초 내 `tp:market.tick.005930` 메시지 ≥ 1건 수신.

### TC-INT-044 — 구독 해제 [P1, SEMI]
- **검증**: 해제 후 30초간 tick 메시지 0건.

### TC-INT-045 — 구독 한도 (400종목) [P1, AUTO]
- **사전조건**: 401종목 구독 시도.
- **검증**: 400건만 구독, 1건은 거부 또는 경고.

---

## 5. 카테고리: 요청 제한 / 성능 (TC-INT-050 ~ 053)

### TC-INT-050 — 1초당 15건 초과 시 자동 페이싱 [P0, AUTO]
- **사전조건**: `RATE_LIMIT_PER_SEC=12` (안전 마진).
- **실행순서**: 1초 내 20건 발주.
- **검증**: 게이트웨이가 자동으로 sleep, CREON에 도달한 요청은 12건/sec 이하.

### TC-INT-051 — 4초당 60건 초과 시 자동 페이싱 [P0, AUTO]
- **검증**: 4초 윈도우에서 CREON에 도달한 요청 ≤ 48건.

### TC-INT-052 — 게이트웨이 응답 시간 SLA [P0, AUTO]
- **검증**: p50 < 300ms, p95 < 800ms (mock), 실 CREON은 + 200ms.

### TC-INT-053 — 동시 요청 처리 (병렬 10) [P1, AUTO]
- **사전조건**: 10개 클라이언트 동시 주문.
- **검증**: 모두 처리, 에러율 0%.

---

## 6. 카테고리: 장애 / 복구 (TC-INT-060 ~ 065)

### TC-INT-060 — 게이트웨이 프로세스 다운 [P0, MANUAL]
- **실행순서**: 게이트웨이 강제 종료.
- **검증**: 본체에서 15초 이내 DOWN 감지, LIVE→SIM 자동 전환.

### TC-INT-061 — 게이트웨이 재기동 후 본체 자동 인식 [P0, MANUAL]
- **사전조건**: 게이트웨이 재기동.
- **검증**: 30초 이내 본체 헬스비트 정상 수신, 운영자 확인 필요 알림.

### TC-INT-062 — Redis 단절 시 게이트웨이 안전 [P0, MANUAL]
- **사전조건**: Redis 종료.
- **검증**: 게이트웨이는 계속 동작 (이벤트 발행 실패만 로그), 주문 API는 정상.

### TC-INT-063 — Redis 복구 후 자동 재연결 [P0, MANUAL]
- **검증**: Redis 재기동 후 30초 이내 헬스비트 발행 재개.

### TC-INT-064 — 미체결 주문 일괄 취소 (Kill Switch) [P0, AUTO]
- **사전조건**: 미체결 5건.
- **실행순서**: Kill Switch 발동.
- **검증**: 5초 이내 미체결 0건, audit_log 1건.

### TC-INT-065 — 부분 취소 실패 처리 [P0, AUTO]
- **사전조건**: 미체결 5건 중 1건은 이미 체결 직전.
- **검증**: 4건 취소 성공, 1건 실패 (`failed[]`에 포함), 502 E0015.

---

## 7. 카테고리: 모드 전환 / Kill Switch (TC-INT-070 ~ 075)

### TC-INT-070 — SIM 모드 사용자 LIVE 주문 시도 [P0, AUTO]
- **사전조건**: 본체 사용자 trade_mode=SIM, 요청 헤더 X-Trade-Mode=LIVE.
- **검증**: HTTP 400, error.code=E0006 (모드 불일치).

### TC-INT-071 — LIVE 전환 7단계 게이트 (실거래 미통과) [P0, AUTO]
- 참조: `52_trading_policy_tests.md` TP-LIVE-001 ~ 008.

### TC-INT-072 — Kill Switch 5초 SLA [P0, AUTO]
- **검증**: 발동 시각 ~ 모든 미체결 취소 완료 시각 < 5초.

### TC-INT-073 — Kill Switch 발동 시 audit 로그 [P0, AUTO]
- **검증**: audit_log 테이블에 (subject, ts, processed_count) 기록.

### TC-INT-074 — 게이트웨이 단절 시 LIVE→SIM 강제 [P0, AUTO]
- 참조: TP-FORCE-SIM-002.

### TC-INT-075 — 일일 손실 한도 도달 시 자동 OFF [P0, AUTO]
- 참조: TP-LOSS-002.

---

## 8. 자동화 매핑

| 자동화 위치 | 케이스 ID |
|---|---|
| `creon-gateway/tests/test_creon_adapter.py` | TC-INT-003, 004, 008, 025~030, 050, 051 |
| `creon-gateway/tests/test_api_endpoints.py` | TC-INT-010~013, 027~031, 042 |
| `creon-gateway/tests/test_healthbeat.py` | TC-INT-006 (mock), 062, 063 |
| `backend/tests/integration/test_creon_e2e.py` | TC-INT-007, 020~023, 030, 064, 065, 070~075 |
| 수동 (Stage 1/2 운영) | TC-INT-001, 002, 005, 014, 015, 020~023, 034, 035, 040, 041, 043, 044, 060, 061 |

---

## 9. 실행 체크리스트

### Stage 1 실행 시
- [ ] TC-INT-001 ~ 015 모두 통과
- [ ] 결과 캡처 (스크린샷 + 로그 라인)

### Stage 2 실행 시
- [ ] TC-INT-020 ~ 053 모두 통과
- [ ] 100건 주문 결과를 일일 리포트에 첨부

### Stage 3 실행 시
- [ ] TC-INT-060 ~ 075 모두 통과
- [ ] 5영업일 운영 일지 작성

---

## 10. 케이스 통계

- 총 케이스 수: **48건**
- P0: 36건
- P1: 9건
- P2: 3건 (v1.1 예정 포함)
- 자동화 가능 (AUTO): 28건
- 반자동 (SEMI): 14건
- 수동 (MANUAL): 6건

---

## 11. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | BackendSenior, QA | 최초 작성, 48 케이스 |
