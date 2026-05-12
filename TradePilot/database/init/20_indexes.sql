-- =====================================================
-- TradePilot - 인덱스 일괄 생성
-- 파일: 20_indexes.sql
-- 본 파일은 PRIMARY KEY / UNIQUE 제약으로 자동 생성된 인덱스 외 추가 인덱스만 정의한다.
-- 파티션 부모에 인덱스를 선언하면 자식 파티션에 자동 전파(PG11+).
-- =====================================================

-- =====================================================
-- 1. tp_user 인덱스
-- =====================================================

-- 관리 화면 필터(역할별)
CREATE INDEX IF NOT EXISTS idx_users_role
    ON tp_user.users (role);

-- 잠금 계정 빠른 조회 (부분 인덱스)
CREATE INDEX IF NOT EXISTS idx_users_locked_until
    ON tp_user.users (locked_until)
    WHERE locked_until IS NOT NULL;

-- 탈퇴 처리(grace period 배치)
CREATE INDEX IF NOT EXISTS idx_users_deleted_at
    ON tp_user.users (deleted_at)
    WHERE deleted_at IS NOT NULL;

-- 세션: 사용자별 만료 정리
CREATE INDEX IF NOT EXISTS idx_sessions_user_expires
    ON tp_user.sessions (user_id, expires_at);

-- OTP: 사용자 + 목적 + 만료 (검증)
CREATE INDEX IF NOT EXISTS idx_otp_user_purpose
    ON tp_user.otp_codes (user_id, purpose, expires_at DESC);

-- 로그인 감사: 사용자별 최신
CREATE INDEX IF NOT EXISTS idx_audit_login_user_ts
    ON tp_user.audit_login (user_id, created_at DESC);

-- 로그인 감사: 기간 스캔(통계용) - BRIN
CREATE INDEX IF NOT EXISTS idx_audit_login_created_brin
    ON tp_user.audit_login USING BRIN (created_at);

-- =====================================================
-- 2. tp_market 인덱스
-- =====================================================

-- 종목명 자동완성/검색 (pg_trgm GIN)
CREATE INDEX IF NOT EXISTS idx_stocks_name_trgm
    ON tp_market.stocks USING GIN (name gin_trgm_ops);

-- 마켓 필터(KOSPI/KOSDAQ)
CREATE INDEX IF NOT EXISTS idx_stocks_market
    ON tp_market.stocks (market);

-- 시총 정렬
CREATE INDEX IF NOT EXISTS idx_stocks_market_cap
    ON tp_market.stocks (market_cap DESC NULLS LAST);

-- 섹터→종목 드릴다운
CREATE INDEX IF NOT EXISTS idx_stock_sectors_sector_stock
    ON tp_market.stock_sectors (sector_id, stock_id);

-- 일봉 기간 스캔(통계/배치) - BRIN
CREATE INDEX IF NOT EXISTS idx_price_daily_date_brin
    ON tp_market.price_daily USING BRIN (trade_date);

-- 분봉 시간 범위 스캔(부모에 선언 → 자식 전파)
CREATE INDEX IF NOT EXISTS idx_price_minute_ts_brin
    ON tp_market.price_minute USING BRIN (ts);

-- 분봉 주기별 차트 (interval_min, stock_id, ts DESC)
CREATE INDEX IF NOT EXISTS idx_price_minute_interval
    ON tp_market.price_minute (interval_min, stock_id, ts DESC);

-- 기업 액션 종목/날짜
CREATE INDEX IF NOT EXISTS idx_corp_action_stock_date
    ON tp_market.corporate_actions (stock_id, effective_date);

-- =====================================================
-- 3. tp_analysis 인덱스
-- =====================================================

-- 과매도 스캐너 (부분 인덱스)
CREATE INDEX IF NOT EXISTS idx_ind_daily_rsi_partial
    ON tp_analysis.indicators_daily (trade_date)
    WHERE rsi14 IS NOT NULL AND rsi14 < 30;

-- 골든크로스(MACD > Signal) 부분 인덱스
CREATE INDEX IF NOT EXISTS idx_ind_daily_macd_golden
    ON tp_analysis.indicators_daily (trade_date)
    WHERE macd IS NOT NULL AND macd_signal IS NOT NULL AND macd > macd_signal;

-- 추천: 일자 + 점수 정렬 (TOP-N)
CREATE INDEX IF NOT EXISTS idx_reco_date_score
    ON tp_analysis.recommendations (trade_date, score DESC);

-- 추천: 전략별
CREATE INDEX IF NOT EXISTS idx_reco_strategy_date
    ON tp_analysis.recommendations (strategy_id, trade_date)
    WHERE strategy_id IS NOT NULL;

-- 추천: 종목별
CREATE INDEX IF NOT EXISTS idx_reco_stock
    ON tp_analysis.recommendations (stock_id);

-- 시그널: 사용자별 최신
CREATE INDEX IF NOT EXISTS idx_signals_user_gen
    ON tp_analysis.signals (user_id, generated_at DESC);

-- 시그널: 활성 (부분 인덱스)
CREATE INDEX IF NOT EXISTS idx_signals_active
    ON tp_analysis.signals (user_id, generated_at DESC)
    WHERE status = 'ACTIVE';

-- 시그널: 종목별
CREATE INDEX IF NOT EXISTS idx_signals_stock_date
    ON tp_analysis.signals (stock_id, generated_at DESC);

-- 시그널: 전략별
CREATE INDEX IF NOT EXISTS idx_signals_strategy
    ON tp_analysis.signals (strategy_id);

-- ML 예측: 종목 + 기준일 + horizon
CREATE INDEX IF NOT EXISTS idx_ml_pred_stock_base
    ON tp_analysis.ml_predictions (stock_id, base_date DESC, horizon);

-- =====================================================
-- 4. tp_trade 인덱스
-- =====================================================

-- 전략: 사용자 + 활성
CREATE INDEX IF NOT EXISTS idx_strategies_user_active
    ON tp_trade.strategies (user_id, active);

-- 전략: 살아있는 전략(소프트삭제 제외) - 부분 인덱스
CREATE INDEX IF NOT EXISTS idx_strategies_user_deleted
    ON tp_trade.strategies (user_id)
    WHERE deleted_at IS NULL;

-- strategy_rules
CREATE INDEX IF NOT EXISTS idx_strategy_rules_strategy
    ON tp_trade.strategy_rules (strategy_id);

-- 주문: 사용자 + 시간 (파티션 부모에 선언 → 자식 전파)
CREATE INDEX IF NOT EXISTS idx_orders_user_ordered
    ON tp_trade.orders (user_id, ordered_at DESC);

-- 주문: 상태 + 모드 (미체결만 - 부분 인덱스)
CREATE INDEX IF NOT EXISTS idx_orders_status_mode
    ON tp_trade.orders (status, trade_mode)
    WHERE status IN ('NEW','PARTIAL','PENDING');

-- 주문: 전략 성과 집계
CREATE INDEX IF NOT EXISTS idx_orders_strategy
    ON tp_trade.orders (strategy_id)
    WHERE strategy_id IS NOT NULL;

-- 주문: 시그널 추적
CREATE INDEX IF NOT EXISTS idx_orders_signal
    ON tp_trade.orders (signal_id)
    WHERE signal_id IS NOT NULL;

-- 주문: 멱등성 키 (사용자+키) UNIQUE
CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_idempotency
    ON tp_trade.orders (user_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- 주문: public_id UNIQUE
CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_public_id
    ON tp_trade.orders (public_id);

-- 주문: 기간 스캔 BRIN
CREATE INDEX IF NOT EXISTS idx_orders_ordered_brin
    ON tp_trade.orders USING BRIN (ordered_at);

-- 체결: 주문 추적
CREATE INDEX IF NOT EXISTS idx_fills_order
    ON tp_trade.fills (order_id);

-- 체결: 사용자별 최신
CREATE INDEX IF NOT EXISTS idx_fills_user_filled
    ON tp_trade.fills (user_id, filled_at DESC);

-- 체결: 종목별
CREATE INDEX IF NOT EXISTS idx_fills_stock_filled
    ON tp_trade.fills (stock_id, filled_at DESC);

-- 체결: 기간 스캔 BRIN
CREATE INDEX IF NOT EXISTS idx_fills_filled_brin
    ON tp_trade.fills USING BRIN (filled_at);

-- 포지션: 사용자 + 모드
CREATE INDEX IF NOT EXISTS idx_positions_user_mode
    ON tp_trade.positions (user_id, trade_mode);

-- 포트폴리오 스냅샷
CREATE INDEX IF NOT EXISTS idx_portfolios_user_snap
    ON tp_trade.portfolios (user_id, snapshot_at DESC);

-- Kill Switch
CREATE INDEX IF NOT EXISTS idx_kill_user_ts
    ON tp_trade.kill_switch_log (user_id, triggered_at DESC);

-- 백테스트: 사용자 + 상태
CREATE INDEX IF NOT EXISTS idx_bt_runs_user_status
    ON tp_trade.backtest_runs (user_id, status, created_at DESC);

-- 백테스트 거래 내역
CREATE INDEX IF NOT EXISTS idx_bt_trades_run
    ON tp_trade.backtest_trades (run_id);

-- =====================================================
-- 5. tp_notify 인덱스
-- =====================================================

-- 알림: 사용자별 시간 정렬(파티션 부모)
CREATE INDEX IF NOT EXISTS idx_noti_user_created
    ON tp_notify.notifications (user_id, created_at DESC);

-- 알림: 미읽음 (부분 인덱스)
CREATE INDEX IF NOT EXISTS idx_noti_unread
    ON tp_notify.notifications (user_id, created_at DESC)
    WHERE read = FALSE;

-- 알림 룰: 사용자 + 이벤트
CREATE INDEX IF NOT EXISTS idx_alert_user_event
    ON tp_notify.alert_rules (user_id, event_type);

-- =====================================================
-- 6. tp_audit 인덱스
-- =====================================================

-- 매매모드 전환: 사용자별
CREATE INDEX IF NOT EXISTS idx_atm_user_ts
    ON tp_audit.audit_trade_mode (user_id, created_at DESC);

-- 주문 이력: 주문 ID
CREATE INDEX IF NOT EXISTS idx_aoh_order
    ON tp_audit.audit_order_history (order_id);

-- 주문 이력: 기간 BRIN
CREATE INDEX IF NOT EXISTS idx_aoh_created_brin
    ON tp_audit.audit_order_history USING BRIN (created_at);

-- 리스크 이벤트
CREATE INDEX IF NOT EXISTS idx_are_user_ts
    ON tp_audit.audit_risk_event (user_id, created_at DESC);

-- 권한 변경
CREATE INDEX IF NOT EXISTS idx_arc_user_ts
    ON tp_audit.audit_role_change (user_id, created_at DESC);

-- =====================================================
-- 7. 통계 정확도 향상 (대용량 시계열 컬럼)
-- =====================================================
ALTER TABLE tp_market.price_minute    ALTER COLUMN ts       SET STATISTICS 500;
ALTER TABLE tp_market.price_minute    ALTER COLUMN stock_id SET STATISTICS 500;
ALTER TABLE tp_market.price_daily     ALTER COLUMN trade_date SET STATISTICS 500;
ALTER TABLE tp_analysis.indicators_daily ALTER COLUMN trade_date SET STATISTICS 500;
ALTER TABLE tp_trade.orders           ALTER COLUMN ordered_at SET STATISTICS 500;
ALTER TABLE tp_trade.fills            ALTER COLUMN filled_at  SET STATISTICS 500;
