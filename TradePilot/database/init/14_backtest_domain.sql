-- =====================================================
-- TradePilot - 백테스트 도메인 DDL
-- 파일: 14_backtest_domain.sql
-- 스키마: tp_trade (백테스트 데이터는 매매 도메인에 포함)
-- 포함: backtest_runs, backtest_results, backtest_trades
-- =====================================================

SET search_path TO tp_trade, public;

-- ----------------------------------------------------
-- backtest_runs : 백테스트 잡 헤더
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.backtest_runs (
    id              BIGSERIAL       PRIMARY KEY,
    job_id          UUID            NOT NULL DEFAULT gen_random_uuid(),
    user_id         BIGINT          NOT NULL,
    strategy_id     BIGINT          NOT NULL,
    universe        JSONB           NOT NULL DEFAULT '[]'::jsonb,            -- 종목 코드 배열
    period_from     DATE            NOT NULL,
    period_to       DATE            NOT NULL,
    initial_capital NUMERIC(20, 4)  NOT NULL,
    slippage        NUMERIC(10, 4)  NOT NULL DEFAULT 0.001,                  -- 0.1%
    fee_rate        NUMERIC(10, 4)  NOT NULL DEFAULT 0.00015,                -- 0.015%
    status          VARCHAR(20)     NOT NULL DEFAULT 'QUEUED',               -- QUEUED/RUNNING/DONE/FAILED/CANCELED
    progress        SMALLINT        NOT NULL DEFAULT 0,                      -- 0~100
    queued_at       TIMESTAMPTZ     NOT NULL DEFAULT now(),
    started_at      TIMESTAMPTZ     NULL,
    finished_at     TIMESTAMPTZ     NULL,
    error_message   TEXT            NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT uq_bt_runs_job_id    UNIQUE (job_id),
    CONSTRAINT fk_bt_runs_user_id   FOREIGN KEY (user_id)     REFERENCES tp_user.users(id)         ON DELETE CASCADE,
    CONSTRAINT fk_bt_runs_strategy  FOREIGN KEY (strategy_id) REFERENCES tp_trade.strategies(id)   ON DELETE CASCADE,
    CONSTRAINT ck_bt_runs_status    CHECK (status IN ('QUEUED','RUNNING','DONE','FAILED','CANCELED')),
    CONSTRAINT ck_bt_runs_progress  CHECK (progress BETWEEN 0 AND 100),
    CONSTRAINT ck_bt_runs_period    CHECK (period_to >= period_from),
    CONSTRAINT ck_bt_runs_capital   CHECK (initial_capital >= 1000000),       -- 최소 100만원
    CONSTRAINT ck_bt_runs_slippage  CHECK (slippage >= 0),
    CONSTRAINT ck_bt_runs_fee       CHECK (fee_rate >= 0 AND fee_rate <= 0.01)
);
COMMENT ON TABLE tp_trade.backtest_runs IS '백테스트 잡 헤더';

-- ----------------------------------------------------
-- backtest_results : 백테스트 결과 (사용자 저장)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.backtest_results (
    run_id              BIGINT          PRIMARY KEY,
    label               VARCHAR(100)    NULL,                                -- 사용자가 부여한 라벨
    cumulative_return   NUMERIC(20, 8)  NULL,                                -- 누적 수익률
    annualized_return   NUMERIC(20, 8)  NULL,                                -- 연환산 수익률
    mdd                 NUMERIC(10, 4)  NULL,                                -- Maximum Drawdown(음수)
    sharpe              NUMERIC(20, 8)  NULL,                                -- 샤프지수
    win_rate            NUMERIC(10, 4)  NULL,                                -- 승률 %
    trade_count         INTEGER         NULL,
    equity_curve        JSONB           NULL,                                -- 자산 시계열
    summary             JSONB           NOT NULL DEFAULT '{}'::jsonb,
    saved_at            TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_bt_results_run FOREIGN KEY (run_id) REFERENCES tp_trade.backtest_runs(id) ON DELETE CASCADE
);
COMMENT ON TABLE tp_trade.backtest_results IS '백테스트 결과 (사용자 저장 시 label 부여)';

-- ----------------------------------------------------
-- backtest_trades : 백테스트 가상 거래 내역
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.backtest_trades (
    id              BIGSERIAL       PRIMARY KEY,
    run_id          BIGINT          NOT NULL,
    stock_id        BIGINT          NOT NULL,
    side            VARCHAR(10)     NOT NULL,                                -- BUY/SELL
    entry_price     NUMERIC(20, 4)  NOT NULL,
    exit_price      NUMERIC(20, 4)  NULL,
    qty             NUMERIC(20, 4)  NOT NULL,
    pnl             NUMERIC(20, 4)  NULL,
    entry_at        TIMESTAMPTZ     NOT NULL,
    exit_at         TIMESTAMPTZ     NULL,
    CONSTRAINT fk_bt_trades_run     FOREIGN KEY (run_id)   REFERENCES tp_trade.backtest_runs(id) ON DELETE CASCADE,
    CONSTRAINT fk_bt_trades_stock   FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id)        ON DELETE RESTRICT,
    CONSTRAINT ck_bt_trades_side    CHECK (side IN ('BUY','SELL'))
);
COMMENT ON TABLE tp_trade.backtest_trades IS '백테스트 가상 거래 타임라인';
