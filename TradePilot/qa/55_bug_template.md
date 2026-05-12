# TradePilot 버그 리포트 템플릿 (Bug Report Template)

> 문서 ID: 55_BUG_TEMPLATE
> 버전: v1.0
> 작성자: QA
> 최종 수정일: 2026-05-12

본 템플릿은 Jira(또는 Notion) 이슈 등록 시 사용한다. **실거래 사고와 직결되는 버그**는 우선순위 Blocker로 즉시 등록하고 PM/DevLead에 1:1 알림한다.

---

## 1. 이슈 ID / 제목 양식

- 이슈 키: `TP-NNNN` (Jira 자동)
- 제목: `[도메인][심각도] 한줄 요약 (영향 범위)`
- 예: `[ORDER][Blocker] LIVE 모드에서 일일 한도 초과 매수가 체결됨 (전 사용자)`

---

## 2. 본문 양식 (필수 섹션)

```markdown
## 1. 요약
한 줄로 무엇이 잘못되었는지.

## 2. 환경
- 환경: Dev / QA(Staging) / Production
- 빌드/버전: vX.Y.Z (commit SHA)
- 사용자 등급: ROLE_TRADER / ROLE_TRADER_PRO / ROLE_OPERATOR / ROLE_ADMIN
- 매매 모드: SIM / LIVE
- 브라우저/OS: Chrome 134 / macOS 15 (E2E의 경우)
- API 호출 시각: KST ISO-8601

## 3. 사전 조건
- 보유 종목 / 잔고 / 한도 설정값
- 시드 데이터 또는 특정 종목 코드
- 시간대 의존성(예: 09:00 직후)

## 4. 재현 단계
1. 로그인 (`user-1@test.local` / `password`)
2. `X-Trade-Mode: LIVE` 헤더로 `POST /api/v1/orders` 호출
3. 페이로드: `{ "code": "005930", "side": "BUY", "qty": 100, "order_type": "MARKET" }`
4. ...

## 5. 기대 결과
- HTTP 422
- `error.code = "E0021"`
- `error.details.limit = 5000000`
- 주문 미체결 + `audit_log` 1건 기록

## 6. 실제 결과
- HTTP 201
- `success = true`, `status = FILLED`
- DB `orders` 테이블에 한도 초과 주문 1건 생성

## 7. 영향도 / 우선순위
- 사용자 영향 범위: 전 사용자 / 일부 / 본인 한정
- 데이터 손상: 예/아니오
- 보안/금전 손실 가능성: 예/아니오
- 우선순위 제안: Blocker / Critical / Major / Minor

## 8. 첨부
- API 요청/응답 JSON (민감정보 마스킹)
- 스크린샷 / 화면 녹화 (E2E)
- DB SELECT 결과 (DBA 협업 시)
- 서버 로그 trace_id

## 9. 회귀 자동화 케이스 추가 제안
- 신규 케이스 ID: TC-ORDER-NNN
- 자동화 위치: `backend/tests/qa/test_*.py::test_*`
```

---

## 3. 우선순위 가이드

| 우선순위 | 정의 | 예시 | 1차 응답 SLA |
|---|---|---|---|
| Blocker | 실거래 사고/금전 손실/로그인 불가 | LIVE 한도 우회, Kill Switch 미작동 | 즉시 |
| Critical | 핵심 기능 사용 불가 | SIM 주문 실패, 차트 비표시 | 30분 |
| Major | 부분 기능 불가, 회피 가능 | 알림 미발송, 특정 필터 오작동 | 4시간 |
| Minor | UI 정렬 / 문구 / 비핵심 | 페이지네이션 표기 오류, 한글 깨짐 | 1영업일 |

> Blocker/Critical은 Jira 자동 알림 + Slack `#qa-alert` 채널 알림 의무.

---

## 4. 워크플로우

```
NEW (등록)
  ↓ DevLead 우선순위 확정
TRIAGED
  ↓ 개발자 배정 + 수정 PR
IN PROGRESS
  ↓ PR 머지 (단위 테스트 + 회귀 자동화 추가)
RESOLVED
  ↓ QA 재현 시나리오 재검증
VERIFIED
  ↓ 다음 릴리즈 포함 확인
CLOSED
```

- Blocker는 NEW → IN PROGRESS 진행 SLA 30분 이내.
- RESOLVED 후 QA 재검증 실패 시 REOPENED.

---

## 5. 데이터 정합성 의심 케이스

다음 항목은 DBA와 협업하여 DB 직접 조회로 검증한다.

| 항목 | 검증 SQL 예시 |
|---|---|
| 주문→체결 정합성 | `SELECT o.id, o.status, COUNT(t.id) FROM orders o LEFT JOIN trades t ON t.order_id=o.id WHERE o.created_at::date = CURRENT_DATE GROUP BY 1,2 HAVING COUNT(t.id) = 0 AND o.status='FILLED'` |
| 잔고 일관성 | `SELECT user_id, code, SUM(qty) FROM trades GROUP BY 1,2 HAVING SUM(qty) <> (SELECT qty FROM portfolios WHERE ...)` |
| 한도 카운터 | `SELECT user_id, SUM(price*qty) FROM trades WHERE side='BUY' AND created_at::date=CURRENT_DATE GROUP BY 1` |
| 감사 로그 누락 | `SELECT id FROM users WHERE trade_mode='LIVE' AND id NOT IN (SELECT user_id FROM audit_log WHERE event='MODE_SWITCH')` |

DBA 협업 결과는 본 양식 9번 회귀 자동화 케이스 추가 제안 절에 SQL과 함께 첨부한다.

---

## 6. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | QA | 최초 작성 |
