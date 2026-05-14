# TradePilot 쿼리 카탈로그 및 EXPLAIN 정성 분석

> 문서 ID: 90_QUERY_CATALOG
> 버전: v1.0
> 작성자: DBA
> 최종 수정일: 2026-05-14

본 문서는 `backend/app/repositories/` 의 SQLAlchemy 코드를 기준으로 운영 환경에서
자주 실행될 것으로 예상되는 쿼리를 카탈로그화하고, **정성적 EXPLAIN 분석**과
**권장 인덱스 / 튜닝 액션**을 제시한다. 실제 운영 데이터가 없는 시점이므로
카디널리티 추정과 실행계획 패턴(B-Tree/Bitmap/Seq Scan)을 기반으로 한다.

---

## 0. 분석 전제(워크로드 모델)

| 항목 | 추정값 |
|---|---|
| 활성 사용자 | 5,000명 (peak 1,000 동시) |
| 종목 수 | ~2,700 (KOSPI+KOSDAQ+ETF) |
| 일봉 행 수 / 년 | 2,700 × 250 영업일 ≈ 675,000 |
| 5년 일봉 누적 | ~3.4M 행 (단일 테이블 가능) |
| 분봉(1m) / 일 / 활성종목 200 | 200 × 390 ≈ 78,000 행/일 |
| 분봉 1년 (1m) | ~19M 행 (월 1.6M) → 파티션 필수 |
| 주문 / 일 (전체) | ~20,000건 (사용자당 4건 × 5,000) |
| 주문 10년 누적 | ~50M 행 → 파티션 필수 |
| 체결 / 주문 비율 | 1.2 |
| 시그널 / 일 / 사용자 | 평균 10건 → 일 50,000건 |
| 알림 / 일 | ~150,000건 (3 채널 × 50,000 이벤트) |

> 카디널리티 가정은 32_INDEX_STRATEGY 와 일치.

---

## 1. 사용자 도메인 (`tp_user`)

| # | 호출 위치 | SQL 요약 | 빈도 | 영향 테이블 | 현재 활용 인덱스 | 예상 계획 | 권장 |
|---|---|---|---|---|---|---|---|
| U-01 | `UserRepository.find_by_email` | `SELECT * FROM users WHERE email=? AND deleted_at IS NULL` | 매 로그인 | `users` | `uq_users_email` | Index Scan (단일행) | 충분 |
| U-02 | `UserRepository.find_by_public_id` | `SELECT * FROM users WHERE public_id=? AND deleted_at IS NULL` | API 호출 시 | `users` | `uq_users_public_id` | Index Scan | 충분 |
| U-03 | `UserRepository.increment_login_fail` | `UPDATE users SET login_fail_count=login_fail_count+1, locked_until=? WHERE id=?` | 로그인 실패 시 | `users` | PK | Index Scan (1행 UPDATE) | 충분 |
| U-04 | `SessionRepository.find_by_hash` | `SELECT * FROM sessions WHERE refresh_token_hash=? AND revoked_at IS NULL AND expires_at>now()` | 토큰 갱신 마다 | `sessions` | `uq_sessions_refresh_hash` | Index Scan + Filter | 충분 (해시 매칭 후 추가 조건은 1행) |
| U-05 | `SessionRepository.revoke_all_for_user` | `UPDATE sessions SET revoked_at=now() WHERE user_id=? AND revoked_at IS NULL` | 비번 변경/로그아웃 | `sessions` | `idx_sessions_user_expires` | Index Scan | **권장: 부분 인덱스 `(user_id) WHERE revoked_at IS NULL`** — `revoked_at` 조건이 자주 동반 |
| U-06 | `SessionRepository.delete_expired` | `DELETE FROM sessions WHERE expires_at < ?` | 1시간 cron | `sessions` | 미사용 인덱스(전체 스캔) | Seq Scan or Index Scan(idx_sessions_user_expires) | **권장: `idx_sessions_expires_at` (단일 컬럼)** |
| U-07 | `OtpRepository.find_active` | `SELECT * FROM otp_codes WHERE otp_id=? AND consumed_at IS NULL` | OTP 검증 시 | `otp_codes` | `uq_otp_otp_id` | Index Scan | 충분 |
| U-08 | 로그인 감사 INSERT | `INSERT INTO audit_login(...)` | 매 로그인 시도 | `audit_login` | - | Insert | 충분 (append-only) |
| U-09 | 로그인 감사 조회 (관리 화면) | `SELECT ... FROM audit_login WHERE user_id=? ORDER BY created_at DESC LIMIT 50` | 관리자 조회 | `audit_login` | `idx_audit_login_user_ts` | Index Scan | 충분 |
| U-10 | 잠금 계정 배치 | `SELECT id FROM users WHERE locked_until < now()` | 매 분 | `users` | `idx_users_locked_until` (partial) | Index Scan (소수) | 충분 |

### 누락 식별
- **U-05/U-06**: `sessions.revoked_at` 조건 + 만료 정리 시 효율 부족 → 인덱스 2종 추가 권장.

---

## 2. 시장 도메인 (`tp_market`)

| # | 호출 위치 | SQL 요약 | 빈도 | 영향 테이블 | 현재 활용 인덱스 | 예상 계획 | 권장 |
|---|---|---|---|---|---|---|---|
| M-01 | `StockExtRepository.find_by_code` | `SELECT * FROM stocks WHERE code=?` | 매우 빈번 | `stocks` | `uq_stocks_code` | Index Scan | 충분 |
| M-02 | `StockExtRepository.search` (이름) | `WHERE name ILIKE '%kk%' OR code LIKE 'k%'` | 검색창 입력 | `stocks` | `idx_stocks_name_trgm` (GIN) | Bitmap Index Scan (trgm) | 충분 (단, ILIKE는 trgm 활용 위해 `Stock.name ILIKE '%q%'` 정확성 확인). prefix `code LIKE 'q%'`은 `uq_stocks_code`로 처리 |
| M-03 | `StockExtRepository.search` (시장 필터) | `WHERE status='LISTED' AND market='KOSPI'` | 검색창 | `stocks` | `idx_stocks_market` | Bitmap | 충분 |
| M-04 | `StockExtRepository.get_primary_sector` | `JOIN stock_sectors ON stock_id=? WHERE is_primary=true` | 종목 상세 | `stock_sectors` | PK | Index Scan | **권장: `(stock_id) WHERE is_primary` 부분 인덱스** (대표 섹터만 조회) |
| M-05 | `StockExtRepository.list_daily` | `WHERE stock_id=? AND trade_date BETWEEN ? AND ? ORDER BY trade_date` | 차트 1회/페이지 | `price_daily` | PK (stock_id, trade_date) | Index Scan, 순방향 | 충분 |
| M-06 | `StockExtRepository.list_minute` | `WHERE stock_id=? AND interval_min=? AND ts BETWEEN ?..?` | 차트 1회/페이지 | `price_minute` | `idx_price_minute_interval` + 파티션 프루닝 | Partition Pruning + Index Scan | 충분 |
| M-07 | `StockExtRepository.latest_daily` | `WHERE stock_id=? ORDER BY trade_date DESC LIMIT 1` | 종목 상세 | `price_daily` | PK | Index Scan Backward | 충분 |
| M-08 | `MarketIndexRepository.latest_daily` | `WHERE index_id=? ORDER BY trade_date DESC LIMIT 1` | 메인 헤더 | `market_index_daily` | PK | Index Scan Backward | 충분 |
| M-09 | `MarketIndexRepository.list_daily` | `WHERE index_id=? AND trade_date BETWEEN ?..?` | 지수 차트 | `market_index_daily` | PK | Index Scan | 충분 |
| M-10 | `SectorRepository.list_stocks` | `JOIN stock_sectors WHERE sector_id=? ORDER BY code` | 섹터→종목 화면 | `stock_sectors`, `stocks` | `idx_stock_sectors_sector_stock` | Nested Loop + Index Scan | 충분 |
| M-11 | `SectorRepository.metrics_for_period` | `WHERE sector_id=? AND trade_date BETWEEN ?..?` | 업종 히트맵 | `sector_metrics_daily` | PK | Index Scan | 충분 |
| M-12 | `SectorRepository.latest_metrics_all` | `각 sector loop: ORDER BY trade_date DESC LIMIT 1` | 업종 메인 | `sector_metrics_daily` | PK | Loop N (=섹터 수) Index Scan Backward | **권장: 머터리얼라이즈드 뷰 `mv_sector_daily_summary`** (현재 N+1 패턴) |
| M-13 | 분봉 적재 INSERT | `INSERT INTO price_minute ...` | 매분 200종목 | `price_minute` | (INSERT 시 PK + BRIN) | Insert (파티션 라우팅) | 충분 |
| M-14 | 일봉 적재 INSERT | `INSERT INTO price_daily ...` | 17:00 일배치 | `price_daily` | PK | Insert | 충분 |
| M-15 | 시총 TOP-N | `SELECT * FROM stocks ORDER BY market_cap DESC LIMIT N` | 메인 위젯 | `stocks` | `idx_stocks_market_cap` | Index Scan | 충분 |

### 누락 식별
- **M-04**: 부분 인덱스 추가 권장.
- **M-12**: 머터리얼라이즈드 뷰 필요.

---

## 3. 분석 도메인 (`tp_analysis`)

| # | 호출 위치 | SQL 요약 | 빈도 | 영향 테이블 | 현재 활용 인덱스 | 예상 계획 | 권장 |
|---|---|---|---|---|---|---|---|
| A-01 | `RecommendationRepository.top_n` | `WHERE trade_date=? ORDER BY score DESC LIMIT 5` | 메인 진입 | `recommendations` | `idx_reco_date_score` | Index Scan + Limit | 충분 |
| A-02 | `RecommendationRepository.list_by_filters` (전략) | `WHERE trade_date=? AND strategy_id=?` | 추천 화면 | `recommendations` | `idx_reco_strategy_date` | Index Scan | 충분 |
| A-03 | `RecommendationRepository.list_by_filters` (섹터) | `JOIN stock_sectors WHERE sector_id=?` | 추천 화면 | `recommendations`, `stock_sectors` | `idx_stock_sectors_sector_stock` + `idx_reco_date_score` | Hash Join | 충분 |
| A-04 | `RecommendationRepository.list_by_filters` (시총) | `JOIN stocks WHERE market_cap >= ?` | 추천 화면 | `stocks` | `idx_stocks_market_cap` | Bitmap And | 충분 |
| A-05 | `RecommendationRepository.find_by_code` | `JOIN stocks WHERE code=? AND trade_date=?` | 종목 상세 | `stocks`, `recommendations` | `uq_stocks_code` + `idx_reco_stock` | Nested Loop | 충분 |
| A-06 | `RecommendationRepository.list_by_filters` 최신일자 추출 | `SELECT MAX(trade_date) FROM recommendations` | 매 요청 | `recommendations` | `idx_reco_date_score` (선두컬럼) | Index Only Scan (가능) | 충분. 단, 인덱스만으로 가능하려면 `(trade_date)` 단독 인덱스 권장 → **`idx_reco_date_score`가 선두 trade_date이므로 OK** |
| A-07 | `SignalRepository.list_for_user` | `JOIN stocks WHERE user_id=? ORDER BY generated_at DESC OFFSET ? LIMIT ?` | 시그널 화면 | `signals`, `stocks` | `idx_signals_user_gen` | Index Scan + Nested Loop | 충분 |
| A-08 | `SignalRepository.list_for_user` (상태 필터) | `... AND status='ACTIVE' ...` | 시그널 화면 | `signals` | `idx_signals_active` (partial) | Index Scan | 충분 |
| A-09 | `SignalRepository.count_summary` (active) | `COUNT(*) WHERE user_id=? AND status='ACTIVE'` | 대시보드 | `signals` | `idx_signals_active` | Index Only Scan (가능) | 충분 |
| A-10 | `SignalRepository.count_summary` (today) | `WHERE user_id=? AND generated_at>=today_start` | 대시보드 | `signals` | `idx_signals_user_gen` | Index Scan | 충분 |
| A-11 | `SignalRepository.count_summary` (ignored) | `WHERE user_id=? AND status='IGNORED'` | 대시보드 | `signals` | `idx_signals_user_gen` | Index Scan + Filter | **권장: `(user_id, status) WHERE status IN ('ACTIVE','IGNORED','EXPIRED')` 추가 검토**. 다만 status별 비율 작아 활성 인덱스로 충분. → **단일 인덱스 `(user_id, status, generated_at DESC)`로 통합 권장** (활성/무시/오늘 1쿼리당 1 인덱스) |
| A-12 | 시그널 적재 INSERT | 매일 1회 50,000건 | `signals` | 인덱스 4종 갱신 | Insert | 부담 적음 (적재 시간대 한정) |
| A-13 | 시그널 상태 전이 UPDATE | `WHERE id=? SET status='EXECUTED'` | 주문 발주 시 | `signals` | PK | Index Scan | 충분 |
| A-14 | `MLPredictionRepository.list_for_stock` | `WHERE stock_id=? AND base_date=? ORDER BY horizon` | 종목 상세 | `ml_predictions` | `idx_ml_pred_stock_base` | Index Scan | 충분 |
| A-15 | 과매도 스캐너 | `WHERE trade_date=? AND rsi14<30` | 일 1회 배치 | `indicators_daily` | `idx_ind_daily_rsi_partial` | Index Only Scan | 충분 |
| A-16 | 골든크로스 스캐너 | `WHERE trade_date=? AND macd>macd_signal` | 일 1회 배치 | `indicators_daily` | `idx_ind_daily_macd_golden` | Index Only Scan | 충분 |
| A-17 | 종목별 지표 (최근 60일) | `WHERE stock_id=? AND trade_date>=?` | 차트 오버레이 | `indicators_daily` | PK | Index Scan | 충분 |

### 누락/개선
- A-11: signals.user_id+status+generated_at 복합 인덱스 통합 검토. **다만 `idx_signals_active` partial 인덱스가 ACTIVE에 매우 효과적이라 유지**.
- A-17 보조: 모든 종목별 최신 지표가 자주 조회된다면 `mv_indicator_summary` 머터리얼라이즈드 뷰 후보.

---

## 4. 매매 도메인 (`tp_trade`)

| # | 호출 위치 | SQL 요약 | 빈도 | 영향 테이블 | 현재 활용 인덱스 | 예상 계획 | 권장 |
|---|---|---|---|---|---|---|---|
| T-01 | `OrderRepository.find_by_public_id` | `WHERE public_id=?` | 주문 상세 | `orders` | `uq_orders_public_id` | Index Scan | 충분 |
| T-02 | `OrderRepository.find_by_idempotency_key` | `WHERE user_id=? AND idempotency_key=? ORDER BY ordered_at DESC LIMIT 1` | 매 발주 전 | `orders` | `uq_orders_idempotency` (partial) | Index Scan | 충분 |
| T-03 | `OrderRepository.count_daily_buys` | `COUNT(*) WHERE user_id=? AND side='BUY' AND status<>'REJECTED' AND ordered_at BETWEEN ?..?` | 매 발주 전 | `orders` | `idx_orders_user_ordered` (파티션 프루닝+) | Index Scan + Filter | **권장: `(user_id, trade_mode, side, ordered_at)` 또는 status 포함 — 현재 status≠'REJECTED' 필터 비용 작음, partial 인덱스 `(user_id, ordered_at) WHERE status<>'REJECTED'`는 과도. 유지 권장** |
| T-04 | `OrderRepository.sum_daily_buy_amount` | `SUM(fill_qty*fill_price) WHERE user_id=? AND filled_at BETWEEN ?..?` | 매 발주 전 | `fills` | `idx_fills_user_filled` (파티션 프루닝+) | Index Scan + Aggregate | 충분 |
| T-05 | `OrderRepository.list_for_user` (기본) | `WHERE user_id=? ORDER BY ordered_at DESC OFFSET ? LIMIT ?` | 주문 이력 화면 | `orders` | `idx_orders_user_ordered` | Index Scan (파티션 프루닝 X — 기간 미지정 시 모든 파티션 스캔) | **권장: 화면 기본값으로 최근 30일 강제(애플리케이션 레벨) — 파티션 프루닝 활용**. 인덱스 자체는 충분 |
| T-06 | `OrderRepository.list_for_user` (status 필터) | `... AND status=?` | 주문 이력 | `orders` | `idx_orders_user_ordered` + status filter | Index Scan + Filter | **권장: `(user_id, status, ordered_at DESC)` 복합 인덱스** — status 필터가 일상적 |
| T-07 | `OrderRepository.list_for_user` (code 필터) | `JOIN stocks WHERE code=?` | 주문 이력 | `stocks`, `orders` | `uq_stocks_code` + `idx_orders_user_ordered` | Nested Loop | 충분 |
| T-08 | 주문 상태 전이 UPDATE | `WHERE id=? AND ordered_at=? SET status=?` | 체결 콜백 | `orders` | PK (id, ordered_at) | Index Scan | 충분 |
| T-09 | 미체결 주문 일괄 조회 (KillSwitch) | `WHERE user_id=? AND status IN ('NEW','PARTIAL','PENDING')` | 비상정지 시 | `orders` | `idx_orders_status_mode` (partial) | Bitmap Index Scan | **권장: user_id 포함 partial `(user_id, status) WHERE status IN(...)`** — 기존 인덱스는 user_id 미포함이라 추가 필터 발생 |
| T-10 | 체결 INSERT | `INSERT INTO fills ...` | 매 체결 | `fills` | 파티션 라우팅 | Insert | 충분 |
| T-11 | 주문→체결 조회 | `WHERE order_id=?` | 주문 상세 | `fills` | `idx_fills_order` | Index Scan | 충분 |
| T-12 | `PositionRepository.find` | `WHERE user_id=? AND stock_id=? AND trade_mode=?` | 매 발주/체결 | `positions` | `uq_positions_user_stock_mode` | Index Scan | 충분 |
| T-13 | `PositionRepository.count_active` | `COUNT(*) WHERE user_id=? AND trade_mode=? AND qty>0` | 발주 전 한도 체크 | `positions` | `idx_positions_user_mode` | Index Scan + Filter | **권장: `(user_id, trade_mode) WHERE qty>0` partial index** — qty>0가 일반 필터 |
| T-14 | `PortfolioRepository.latest_snapshot` | `WHERE user_id=? AND trade_mode=? ORDER BY snapshot_at DESC LIMIT 1` | 대시보드 | `portfolios` | `idx_portfolios_user_snap` | Index Scan Backward + Filter | **권장: `(user_id, trade_mode, snapshot_at DESC)` 복합** — trade_mode 필터 효율화 |
| T-15 | `PortfolioRepository.positions_with_stock` | `JOIN stocks WHERE user_id=? AND trade_mode=? AND qty>0 ORDER BY opened_at DESC` | 대시보드 | `positions`, `stocks` | `idx_positions_user_mode` | Nested Loop | 충분 |
| T-16 | `DailyPnlRepository.list_for_period` | `WHERE user_id=? AND trade_mode=? AND trade_date BETWEEN ?..?` | 손익 차트 | `daily_pnl` | PK (user_id, trade_date, trade_mode) | Index Scan | 충분 |
| T-17 | 사용자 누적 PnL | `SUM(realized_pnl + unrealized_pnl) WHERE user_id=?` | 메인 위젯 | `daily_pnl` | PK | Index Scan + Aggregate | **권장: `mv_user_pnl_summary` 머터리얼라이즈드 뷰** (사용자 5,000 × 일 250일 → 1.25M 행을 매 페이지 로드 시 집계는 부담) |
| T-18 | `StrategyRepository.list_for_user` | `WHERE user_id=? AND deleted_at IS NULL ORDER BY created_at DESC` | 전략 화면 | `strategies` | `idx_strategies_user_deleted` (partial) | Index Scan | 충분 |
| T-19 | `StrategyRepository.list_for_user` (active) | `... AND active=?` | 전략 화면 | `strategies` | `idx_strategies_user_active` | Index Scan | 충분 |
| T-20 | Strategy 활성 토글 | `UPDATE strategies SET active=? WHERE id=?` | 사용자 액션 | `strategies` | PK | Index Scan | 충분 |
| T-21 | `BacktestRunRepository.find_by_job_id` | `WHERE job_id=?` | 잡 상태 폴링 | `backtest_runs` | `uq_bt_runs_job_id` | Index Scan | 충분 |
| T-22 | `BacktestResultRepository.list_saved_for_user` | `JOIN runs WHERE user_id=? ORDER BY saved_at DESC` | 저장 결과 화면 | `backtest_results`, `backtest_runs` | `idx_bt_runs_user_status` | Hash Join | **권장: `idx_bt_results_saved_at` (saved_at DESC) — runs 거쳐 user 필터, runs 인덱스가 driver. 충분** |
| T-23 | `BacktestTradeRepository.list_for_run` | `WHERE run_id=? ORDER BY entry_at` | 결과 상세 | `backtest_trades` | `idx_bt_trades_run` | Index Scan | 충분 |
| T-24 | Kill Switch 이력 조회 | `WHERE user_id=? ORDER BY triggered_at DESC LIMIT N` | 보안 화면 | `kill_switch_log` | `idx_kill_user_ts` | Index Scan | 충분 |

### 누락 식별
- **T-06**: orders (user_id, status, ordered_at DESC) 복합.
- **T-09**: orders user_id 포함 미체결 partial.
- **T-13**: positions qty>0 partial.
- **T-14**: portfolios trade_mode 포함 복합.
- **T-17**: PnL MV.

---

## 5. 알림 도메인 (`tp_notify`)

| # | 호출 위치 | SQL 요약 | 빈도 | 영향 테이블 | 현재 활용 인덱스 | 예상 계획 | 권장 |
|---|---|---|---|---|---|---|---|
| N-01 | `NotificationRepository.list_for_user` | `WHERE user_id=? ORDER BY created_at DESC OFFSET ? LIMIT ?` | 알림 화면 | `notifications` | `idx_noti_user_created` | Index Scan + 파티션 프루닝(기간 미지정 시 X) | 충분 (단, 기간 미지정 시 전 파티션 스캔 가능 — 화면에서 최근 90일 강제 권장) |
| N-02 | `NotificationRepository.list_for_user` (unread) | `... AND read=false` | 알림 뱃지 | `notifications` | `idx_noti_unread` (partial) | Index Only Scan (가능) | 충분 |
| N-03 | `NotificationRepository.mark_read` | `UPDATE WHERE id=? AND user_id=?` | 단건 클릭 | `notifications` | PK (id, created_at) — id만으로는 파티션 프루닝 불가 | **주의**: id만으로 WHERE → 전체 파티션 스캔 발생. **권장: 호출부에서 created_at 같이 전달**, 또는 글로벌 인덱스 대안 없음. 운영상 단건 UPDATE 비용 작아 허용 |
| N-04 | `NotificationRepository.mark_read_all` | `UPDATE WHERE user_id=? AND read=false` | 일괄 클릭 | `notifications` | `idx_noti_unread` | Index Scan | 충분 |
| N-05 | 알림 적재 INSERT | 일 ~150,000건 | `notifications` | 인덱스 갱신 | Insert | 충분 |
| N-06 | 알림 룰 매칭 | `WHERE user_id=? AND event_type=? AND active=true` | 이벤트 발생 시 | `alert_rules` | `idx_alert_user_event` | Index Scan + Filter (active) | **권장: `(user_id, event_type) WHERE active=true` partial** |
| N-07 | 알림 발송 대기 큐 | `WHERE sent_at IS NULL ORDER BY created_at LIMIT N` | Celery worker | `notifications` | 미사용 인덱스(전체 스캔) | Seq Scan or PK | **권장: `(created_at) WHERE sent_at IS NULL` partial — 발송 큐 패턴** |

### 누락 식별
- **N-06**: alert_rules partial.
- **N-07**: notifications 발송 대기 partial. (현 시점 N-07 SQL은 reposition 코드엔 없지만 워커가 사용할 가능성 높음)

---

## 6. 감사 도메인 (`tp_audit`)

| # | 호출 위치 | SQL 요약 | 빈도 | 영향 테이블 | 현재 활용 인덱스 | 예상 계획 | 권장 |
|---|---|---|---|---|---|---|---|
| AU-01 | trade_mode 전환 조회 | `WHERE user_id=? ORDER BY created_at DESC` | 감사 화면 | `audit_trade_mode` | `idx_atm_user_ts` | Index Scan | 충분 |
| AU-02 | order 이력 추적 | `WHERE order_id=?` | 주문 상세 | `audit_order_history` | `idx_aoh_order` | Index Scan | 충분 |
| AU-03 | order 이력 INSERT | 매 상태 전이 | `audit_order_history` | 파티션 라우팅 | Insert | 충분 |
| AU-04 | risk 이벤트 조회 (사용자) | `WHERE user_id=? ORDER BY created_at DESC` | 감사 화면 | `audit_risk_event` | `idx_are_user_ts` | Index Scan | 충분 |
| AU-05 | risk 이벤트 조회 (severity) | `WHERE severity='CRITICAL' AND created_at >= ?` | 운영자 알람 | `audit_risk_event` | 미사용 인덱스(`idx_are_user_ts`는 user_id 선두) | Seq Scan | **권장: `(severity, created_at DESC) WHERE severity IN ('WARN','CRITICAL')` partial** |
| AU-06 | role 변경 이력 | `WHERE user_id=? ORDER BY created_at DESC` | 감사 화면 | `audit_role_change` | `idx_arc_user_ts` | Index Scan | 충분 |

### 누락 식별
- **AU-05**: risk severity 인덱스.

---

## 7. EXPLAIN 정성 분석 — 대표 쿼리 시뮬레이션

### 7.1 T-05 사용자 주문 이력 (기간 미지정)

```sql
SELECT * FROM tp_trade.orders
 WHERE user_id = 12345
 ORDER BY ordered_at DESC
 LIMIT 20 OFFSET 0;
```

**예상 계획 (현재 인덱스):**
```
Limit (cost=0..X rows=20)
  -> Append (all monthly partitions, NO pruning)
        -> Index Scan Backward using idx_orders_user_ordered on orders_y2026m05
        -> Index Scan Backward using idx_orders_user_ordered on orders_y2026m04
        ... (모든 파티션)
  -> Merge Append (각 파티션 결과 merge)
```

**문제**: 파티션 프루닝 미작동 → 30개 파티션을 모두 스캔.
**대책**: ① 화면 기본값으로 `from_dt` 강제(최근 30일), ② `idx_orders_user_ordered`가 각 파티션에 존재하므로 Index Scan Backward + Limit 으로 첫 20개에서 종료 → 비용은 낮으나 파티션 N개 진입 오버헤드.

### 7.2 T-06 사용자 주문 이력 (status 필터)

```sql
SELECT * FROM tp_trade.orders
 WHERE user_id = 12345 AND status = 'FILLED'
 ORDER BY ordered_at DESC
 LIMIT 20;
```

**현재**: `idx_orders_user_ordered` Index Scan + Filter(status) → status 카디널리티 낮으면 다수 스킵 후 20행 도출.
**개선**: `(user_id, status, ordered_at DESC)` 복합 인덱스 → Filter 제거.

### 7.3 T-13 포지션 활성 카운트

```sql
SELECT COUNT(*) FROM tp_trade.positions
 WHERE user_id = 12345 AND trade_mode = 'LIVE' AND qty > 0;
```

**현재**: `idx_positions_user_mode` Index Scan + Filter(qty>0).
**개선**: `(user_id, trade_mode) WHERE qty>0` partial → 작은 인덱스로 빠른 카운트.

### 7.4 T-09 미체결 일괄 조회 (KillSwitch)

```sql
SELECT * FROM tp_trade.orders
 WHERE user_id = 12345
   AND status IN ('NEW','PARTIAL','PENDING');
```

**현재**: `idx_orders_status_mode` (status+trade_mode partial) — user_id 미포함 → 전체 미체결 행을 status로 필터 후 user_id Filter.
**개선**: `(user_id, status) WHERE status IN(...)` partial → user_id 선두로 즉시 좁힘.

### 7.5 M-12 섹터 최신 메트릭 (N+1)

```python
for sector in sectors:  # 30~50개
    SELECT * FROM sector_metrics_daily
     WHERE sector_id = ? ORDER BY trade_date DESC LIMIT 1;
```

**문제**: N개 쿼리 round-trip.
**대책**: 머터리얼라이즈드 뷰 `mv_sector_daily_summary`로 단일 SELECT 변환.

### 7.6 T-17 사용자 누적 PnL

```sql
SELECT SUM(realized_pnl), SUM(unrealized_pnl)
  FROM tp_trade.daily_pnl
 WHERE user_id = 12345 AND trade_mode = 'LIVE';
```

**예상 계획**: PK Index Scan + Aggregate. 데이터 250일 × 사용자 5,000 → 사용자 1명 250행 → 빠름. **다만 대시보드 진입 시 매번 집계 → 머터리얼라이즈드 뷰로 대체 시 1행 조회로 단순화**.

---

## 8. 추가 권장 인덱스 요약

| # | 인덱스명 | 컬럼 | 종류 | 우선순위 | 정당화 쿼리 |
|---|---|---|---|---|---|
| 1 | `idx_sessions_active_user` | `(user_id) WHERE revoked_at IS NULL` | Partial | High | U-05 |
| 2 | `idx_sessions_expires_at` | `(expires_at)` | B-Tree | High | U-06 |
| 3 | `idx_stock_sectors_primary` | `(stock_id) WHERE is_primary` | Partial | Mid | M-04 |
| 4 | `idx_orders_user_status_ordered` | `(user_id, status, ordered_at DESC)` | B-Tree | High | T-06 |
| 5 | `idx_orders_user_open` | `(user_id, status) WHERE status IN ('NEW','PARTIAL','PENDING')` | Partial | High | T-09 |
| 6 | `idx_positions_user_active` | `(user_id, trade_mode) WHERE qty>0` | Partial | High | T-13 |
| 7 | `idx_portfolios_user_mode_snap` | `(user_id, trade_mode, snapshot_at DESC)` | B-Tree | High | T-14 |
| 8 | `idx_alert_user_event_active` | `(user_id, event_type) WHERE active` | Partial | Mid | N-06 |
| 9 | `idx_noti_pending_send` | `(created_at) WHERE sent_at IS NULL` | Partial | High | N-07 |
| 10 | `idx_are_severity_ts` | `(severity, created_at DESC) WHERE severity IN ('WARN','CRITICAL')` | Partial | Mid | AU-05 |
| 11 | `idx_audit_login_attempt_user` | `(user_id, created_at DESC) WHERE result='FAIL'` | Partial | Low | 보안 모니터 |
| 12 | `idx_kill_switch_recent` | `(triggered_at DESC) WHERE triggered_at > now() - interval '30 days'` (정적 대체: `(triggered_at DESC)` 단일) | B-Tree | Low | 운영자 화면 |

---

## 9. 중복/저사용 인덱스 후보 (운영 후 재검토)

다음 인덱스는 운영 6개월 후 `pg_stat_user_indexes`로 사용도 확인 후 제거 검토:

| 인덱스 | 사유 | 비고 |
|---|---|---|
| `idx_signals_strategy` | strategy별 시그널 조회 빈도 낮을 가능성 | 백테스트 화면이 strategy_id로 시그널 조회한다면 유지 |
| `idx_reco_stock` | `find_by_code`에서 stock_id 조회. 빈도 적으면 제거 가능 | A-05 빈도 모니터 |
| `idx_fills_stock_filled` | 종목별 체결 이력 화면 사용도 낮을 가능성 | 종목 상세 페이지 트래픽 의존 |
| `idx_orders_strategy` (partial) | strategy 성과 집계 빈도 낮으면 제거 가능 | 분기별 리포트라면 ANALYZE 시점 인덱스 활용도 낮음 |

> 인덱스 제거는 **3개월 이상 idx_scan=0 인 경우만**, 그리고 운영자 확인 후 수행한다.

---

## 10. 머터리얼라이즈드 뷰 후보

| MV | 갱신 주기 | 사용 화면 | 대체 쿼리 |
|---|---|---|---|
| `tp_market.mv_sector_daily_summary` | 매일 17:00 (장마감 후) | 업종 분석 메인, 섹터 히트맵 | M-12 N+1 제거 |
| `tp_analysis.mv_indicator_summary` | 매일 17:30 (지표 계산 후) | 종목 검색 결과 + 지표 오버레이 | A-17 보조 (필요 시) |
| `tp_trade.mv_user_pnl_summary` | 매일 18:00 (PnL 산출 후) | 대시보드 누적 PnL, 마이페이지 | T-17 |

상세 정의는 `migrations/2026_05_add_materialized_views.sql` 참조.

---

## 11. 운영 적용 우선순위

| 우선순위 | 항목 | 적용 시점 |
|---|---|---|
| P0 | T-09 미체결 partial (KillSwitch 응답시간 직접 영향) | 즉시 |
| P0 | T-06 user_status_ordered (주문 이력 핵심) | 즉시 |
| P1 | T-13 positions active partial | 1주 |
| P1 | T-14 portfolios 복합 | 1주 |
| P1 | mv_sector_daily_summary | 1주 |
| P2 | mv_user_pnl_summary | 2주 |
| P2 | U-05/06 sessions 인덱스 | 2주 |
| P3 | 나머지 (감사, 알림 partial) | 1개월 |
