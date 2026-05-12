# TradePilot API 요구사항 정의서

> 문서 ID: 13_API_REQUIREMENTS
> 버전: v1.0
> 작성자: Planner
> 최종 수정일: 2026-05-12

본 문서는 백엔드(Python FastAPI) 구현 대상이 되는 REST API 엔드포인트 명세를 정의한다.
모든 엔드포인트는 `/api/v1` 접두사를 가진다.

---

## 0. 공통 규약

### 0.1 인증
- 헤더: `Authorization: Bearer {access_token}`
- `/auth/*`, `/public/*`를 제외한 모든 API는 인증 필수.
- 실거래 모드 분기가 필요한 호출은 `X-Trade-Mode: SIM | LIVE` 헤더 동시 전송.

### 0.2 공통 응답 포맷
```
성공:
{ "success": true, "data": <object|array> }

실패:
{ "success": false, "error": { "code": "E0001", "message": "...", "details": {...} } }

페이지:
{ "success": true, "data": { "items": [...], "page": 1, "size": 20, "total": 145, "has_next": true } }
```

### 0.3 페이지네이션 / 정렬
- 쿼리: `page`(1-based, default 1), `size`(default 20, max 100), `sort`(예: `score,desc`)
- 정렬 가능 필드는 엔드포인트별로 명시.

### 0.4 날짜/시간
- 입력: ISO-8601(`2026-05-12T09:00:00+09:00`) 또는 `YYYY-MM-DD`
- 출력: ISO-8601 UTC + Offset, 또는 epoch milliseconds (시계열 응답)

### 0.5 멱등성
- 주문 생성 등 자원 변경 API는 `X-Idempotency-Key`(UUID) 권장. 24시간 내 동일 키 재요청 시 기존 결과 반환.

### 0.6 Rate Limit
| 구간 | 정책 |
|---|---|
| 인증 API | 분당 10회 |
| 시세/지표 조회 | 초당 10회 |
| 주문 생성 | 초당 3회, 일 1,000건 |
| 일반 조회 | 분당 600회 |

---

## 1. Auth (인증) `/api/v1/auth`

| Method | Path | 요청 | 응답 (data) | 에러 코드 |
|---|---|---|---|---|
| POST | `/auth/signup` | `{ email, password, nickname }` | `{ user_id, status }` | E0003, E0051 |
| POST | `/auth/login` | `{ email, password }` | `{ access_token, refresh_token, expires_in }` | E0001, E0052 |
| POST | `/auth/logout` | - | `{ logged_out: true }` | E0001 |
| POST | `/auth/refresh` | `{ refresh_token }` | `{ access_token, expires_in }` | E0001 |
| POST | `/auth/verify-email` | `{ token }` | `{ verified: true }` | E0053 |
| POST | `/auth/password/reset-request` | `{ email }` | `{ sent: true }` | E0003 |
| POST | `/auth/password/reset-confirm` | `{ token, new_password }` | `{ reset: true }` | E0054 |
| POST | `/auth/otp/send` | `{ phone, purpose }` | `{ otp_id, expires_in }` | E0003 |
| POST | `/auth/otp/verify` | `{ otp_id, code }` | `{ otp_token }` | E0011, E0053 |

---

## 2. Users (사용자) `/api/v1/users`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/users/me` | - | `{ id, email, nickname, role, trade_mode, created_at }` | E0001 |
| PATCH | `/users/me` | `{ nickname?, phone? }` | 수정된 사용자 객체 | E0003 |
| GET | `/users/me/settings` | - | 설정 객체 | E0001 |
| PATCH | `/users/me/settings` | 설정 객체(부분) | 수정 결과 | E0003 |
| GET | `/users` (ADMIN) | filter, page | 사용자 페이지 | E0002 |
| PATCH | `/users/{id}/role` (ADMIN) | `{ role }` | 결과 | E0002, E0003 |

---

## 3. Stocks (종목/시세) `/api/v1/stocks`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/stocks/search` | `q, market, page, size` | 종목 페이지 `{code, name, market, sector}` | E0003 |
| GET | `/stocks/{code}` | - | 종목 메타 | E0003 |
| GET | `/stocks/{code}/quote` | - | 실시간 시세 `{price, change, change_pct, volume, ts}` | E0004 |
| GET | `/stocks/{code}/candles` | `interval(D|W|M|1m|5m|15m|30m), from, to` | OHLCV 배열 | E0003 |
| GET | `/stocks/{code}/orderbook` | - | 호가 10단계 | E0004 |
| POST | `/stocks/favorites` | `{ code }` | 결과 | E0001 |
| DELETE | `/stocks/favorites/{code}` | - | 결과 | E0001 |
| GET | `/stocks/favorites` | - | 즐겨찾기 리스트 | E0001 |

정렬 가능 필드: candles 응답은 `ts ASC` 고정.

---

## 4. Indicators (지표) `/api/v1/indicators`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/indicators/ma` | `code, period(반복), interval, from, to` | `{ period: [..values..] }` | E0003 |
| GET | `/indicators/rsi` | `code, period=14, interval, from, to` | 시계열 | E0003 |
| GET | `/indicators/macd` | `code, fast=12, slow=26, signal=9, ...` | `{ macd, signal, hist }` | E0003 |
| GET | `/indicators/bollinger` | `code, period=20, k=2, ...` | `{ mid, upper, lower }` | E0003 |
| GET | `/indicators/obv` | `code, interval, from, to` | 시계열 | E0003 |
| GET | `/indicators/vwap` | `code, interval, from, to` | 시계열 | E0003 |
| GET | `/indicators/stochastic` | `code, k=14, d=3, smooth=3, ...` | `{ k, d }` | E0003 |
| POST | `/indicators/batch` | `{ code, indicators:[{name, params}], interval, from, to }` | 다중 지표 한번에 | E0003 |

---

## 5. Sectors (업종/섹터) `/api/v1/sectors`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/sectors` | - | 섹터 마스터 리스트 | - |
| GET | `/sectors/ranking` | `period(D|W|M), sort` | `[{code, name, change_pct, volume_amount}]` | E0003 |
| GET | `/sectors/flow` | `period` | `[{code, inflow_amount, outflow_amount, net}]` | E0003 |
| GET | `/sectors/heatmap` | `window=30` | 상관계수 매트릭스 `{labels, matrix}` | - |
| GET | `/sectors/{code}/stocks` | `sort, page, size` | 종목 페이지 | E0003 |

---

## 6. Recommendations (추천주) `/api/v1/recommendations`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/recommendations` | `strategy_id?, sector?, market_cap_min?, market_cap_max?, sort, page, size` | 추천 페이지 `{code, name, score, reason, current_price, change_pct}` | E0003 |
| GET | `/recommendations/top` | `limit=5` | TOP 리스트 | - |
| GET | `/recommendations/{code}/detail` | - | 종목 상세 + 지표 + ML 예측 + 키워드 | E0003 |
| GET | `/recommendations/strategies` | - | 추천 산출에 사용된 전략 메타 | - |

정렬 가능: `score, change_pct, volume`.

---

## 7. Signals (매매 시그널) `/api/v1/signals`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/signals` | `status?, strategy_id?, code?, from?, to?, page, size` | 시그널 페이지 `{id, code, action(BUY|SELL), price, confidence, status, created_at}` | E0003 |
| GET | `/signals/{id}` | - | 시그널 상세 + 조건 트레이스 | E0003 |
| POST | `/signals/{id}/ignore` | - | 결과 | E0003 |
| GET | `/signals/active/count` | - | `{ active, today, ignored }` | - |
| POST | `/signals/test` (ADMIN) | `{ strategy_id, code }` | 강제 평가 결과 | E0002 |

---

## 8. Strategies (전략) `/api/v1/strategies`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/strategies` | `active?, page, size` | 전략 페이지 | - |
| POST | `/strategies` | `{ name, description, entry_rules, exit_rules, universe, limits }` | 전략 객체 | E0003 |
| GET | `/strategies/{id}` | - | 전략 객체 | E0003 |
| PATCH | `/strategies/{id}` | 부분 필드 | 수정 결과 | E0003 |
| DELETE | `/strategies/{id}` | - | 결과 | E0003 |
| PATCH | `/strategies/{id}/activate` | `{ active }` | 결과 + 활성 시각 | E0002, E0003 |
| GET | `/strategies/{id}/performance` | `period` | 전략 성과 지표 | E0003 |

전략 룰 표현: JSON DSL (예: `{ "all": [{"indicator":"RSI","op":"<","value":30}, ...] }`).

---

## 9. Orders (주문/체결) `/api/v1/orders`

> 모든 주문 API는 `X-Trade-Mode` 헤더 필수.

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/orders` | `status?, from?, to?, code?, page, size` | 주문 페이지 | E0003 |
| GET | `/orders/{id}` | - | 주문 상세 + 체결 로그 | E0003 |
| POST | `/orders` | `{ code, side(BUY|SELL), qty, order_type(MARKET|LIMIT), price?, strategy_id? }` | 주문 객체 | E0021, E0022, E0023, E0024 |
| POST | `/orders/{id}/cancel` | - | 취소 결과 | E0023 |
| POST | `/orders/liquidate-all` | `{ reason? }` | 강제 청산 결과 | E0023, E0025 |
| GET | `/orders/executions` | `from?, to?, code?, page, size` | 체결 페이지 | E0003 |

멱등성: POST 주문은 `X-Idempotency-Key` 필수.

---

## 10. Portfolios (보유/자산) `/api/v1/portfolios`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/portfolios/summary` | - | `{ total_value, cash, equity, daily_pnl, daily_pnl_pct }` | E0001 |
| GET | `/portfolios/positions` | `page, size` | 보유 종목 페이지 | E0001 |
| GET | `/portfolios/history` | `from, to, granularity(D|W|M)` | 자산 추이 시계열 | E0003 |
| GET | `/portfolios/realized-pnl` | `from, to` | 실현 손익 요약 | E0003 |

---

## 11. Backtest (백테스트) `/api/v1/backtest`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| POST | `/backtest/jobs` | `{ strategy_id, universe[], from, to, initial_capital, slippage, fee_rate }` | `{ job_id, status: QUEUED }` | E0003 |
| GET | `/backtest/jobs/{id}/progress` | - | `{ status, percent, eta_seconds }` | E0003 |
| GET | `/backtest/jobs/{id}/result` | - | `{ summary, equity_curve, trades, metrics }` | E0003, E0031 |
| POST | `/backtest/jobs/{id}/cancel` | - | 결과 | E0003 |
| POST | `/backtest/results/{id}/save` | `{ label }` | 결과 | E0003 |
| GET | `/backtest/results` | `page, size` | 저장된 결과 페이지 | - |
| POST | `/backtest/compare` | `{ result_ids: string[] }` | 비교 데이터 | E0003 |

---

## 12. ML Predictions `/api/v1/ml-predictions`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/ml-predictions/{code}` | `horizon=1..5` | `{ code, predictions:[{date, mean, lower, upper}], model_version }` | E0003, E0041 |
| GET | `/ml-predictions/{code}/accuracy` | `period` | `{ mape, direction_accuracy }` | E0003 |
| POST | `/ml-predictions/retrain` (ADMIN) | `{ codes?: string[], full: bool }` | `{ job_id }` | E0002 |
| GET | `/ml-predictions/jobs/{id}` (ADMIN) | - | 학습 작업 상태 | E0002 |

---

## 13. Market (시장 지수) `/api/v1/market`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/market/indices` | - | `[{code:KOSPI|KOSDAQ, value, change, change_pct, ts}]` | E0004 |
| GET | `/market/indices/{code}/candles` | `interval, from, to` | OHLC 시계열 | E0003 |
| GET | `/market/status` | - | `{ session: PRE|OPEN|CLOSED, next_open, holiday: bool }` | - |
| GET | `/market/calendar` | `year` | 휴장일 리스트 | E0003 |

---

## 14. Notifications (알림) `/api/v1/notifications`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/notifications` | `read?, page, size` | 알림 페이지 | E0001 |
| PATCH | `/notifications/{id}/read` | - | 결과 | E0003 |
| POST | `/notifications/read-all` | - | 결과 | E0001 |
| GET | `/notifications/channels` | - | 채널 설정 | E0001 |
| PATCH | `/notifications/channels` | 설정 객체 | 수정 결과 | E0003 |
| POST | `/notifications/test` | `{ channel }` | 테스트 발송 결과 | E0003 |

---

## 15. Settings (설정) `/api/v1/settings`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/settings/trade-mode` | - | `{ mode: SIM|LIVE, switched_at }` | E0001 |
| POST | `/settings/trade-mode/switch` | `{ target: SIM|LIVE, otp_token?, terms_token? }` | `{ mode, switched_at }` | E0011, E0012, E0013, E0014 |
| GET | `/settings/risk-limits` | - | 한도 객체 | E0001 |
| PUT | `/settings/risk-limits` | `{ daily_buy_amount, daily_buy_count, per_stock_amount, stop_loss_pct, take_profit_pct, daily_loss_limit_pct }` | 결과 | E0003 |
| POST | `/settings/kill-switch` | `{ reason? }` | `{ canceled_orders, failed }` | E0015 |
| GET | `/settings/schedules` | - | 스케줄 객체 | - |
| PUT | `/settings/schedules` | 스케줄 객체 | 결과 | E0003 |
| GET | `/settings/creon` | - | `{ connected, account_masked, last_check_at }` | E0001 |
| POST | `/settings/creon/test` | `{ password_token }` | 연결 테스트 결과 | E0012 |

---

## 16. Reports (수익률 리포트) `/api/v1/reports`

| Method | Path | 요청 | 응답 | 에러 |
|---|---|---|---|---|
| GET | `/reports/pnl` | `from, to, granularity(D|W|M)` | `{ series, summary }` | E0003 |
| GET | `/reports/positions` | `from, to` | 종목별 손익 | E0003 |
| GET | `/reports/trades` | `from, to, status?, code?, page, size` | 거래 페이지 | E0003 |
| GET | `/reports/strategies` | `strategy_ids[]` | 전략별 성과 비교 | E0003 |
| POST | `/reports/export` | `{ type, from, to, format: csv|xlsx }` | `{ export_id }` | E0003 |
| GET | `/reports/export/{id}` | - | `{ status, download_url?, expires_at }` | E0003 |

---

## 17. WebSocket (실시간 채널)

| Path | 메시지 종류 | 비고 |
|---|---|---|
| `/ws/quotes` | `subscribe`, `quote`, `unsubscribe` | 시세 push, JWT 쿼리 인증 |
| `/ws/signals` | `signal`, `order_update` | 사용자별 채널 |
| `/ws/notifications` | `notification` | 인앱 알림 push |

---

## 18. Admin (운영) `/api/v1/admin`

| Method | Path | 설명 | 권한 |
|---|---|---|---|
| GET | `/admin/system/health` | 헬스 체크 + 외부 의존성 상태 | ADMIN/OPERATOR |
| POST | `/admin/system/maintenance` | 유지보수 모드 토글 | ADMIN |
| POST | `/admin/data/refresh/master` | 종목 마스터/섹터 갱신 | OPERATOR |
| GET | `/admin/audit-logs` | 감사 로그 조회 | ADMIN |

---

## 19. 핵심 에러 코드 (요약)
> 상세는 `14_exception_policy.md` 참조

| 코드 | 의미 |
|---|---|
| E0001 | 인증 실패 |
| E0002 | 권한 부족 |
| E0003 | 검증 실패 |
| E0004 | 외부 시스템 장애 |
| E0005 | 서버 내부 오류 |
| E0006 | 매매 모드 불일치 |
| E0007 | 장 외 시간 |
| E0011 | OTP 오류 |
| E0012 | 크레온 연결 실패 |
| E0013 | 약관 미동의 |
| E0014 | 미체결 주문 취소 실패 |
| E0015 | Kill Switch 부분 실패 |
| E0021 | 한도 초과 |
| E0022 | 중복 주문 |
| E0023 | 증권사 주문 에러 |
| E0024 | 증거금 부족 |
| E0025 | 강제 청산 부분 실패 |
| E0031 | 백테스트 결과 만료 |
| E0041 | ML 모델 미학습 |
| E0042 | ML 학습 실패 |
| E0051 | 이메일 중복 |
| E0052 | 계정 잠금 |
| E0053 | OTP/토큰 만료 |
| E0054 | 비밀번호 재설정 토큰 오류 |

---

## 20. 엔드포인트 수 집계
| 도메인 | 엔드포인트 수 |
|---|---:|
| Auth | 9 |
| Users | 6 |
| Stocks | 8 |
| Indicators | 8 |
| Sectors | 5 |
| Recommendations | 4 |
| Signals | 5 |
| Strategies | 7 |
| Orders | 6 |
| Portfolios | 4 |
| Backtest | 7 |
| ML Predictions | 4 |
| Market | 4 |
| Notifications | 6 |
| Settings | 9 |
| Reports | 6 |
| WebSocket | 3 |
| Admin | 4 |
| **합계** | **105** |

---

## 21. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | Planner | 최초 작성 |
