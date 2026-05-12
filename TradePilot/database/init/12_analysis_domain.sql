-- =====================================================
-- TradePilot - 분석 도메인 DDL
-- 파일: 12_analysis_domain.sql
-- 스키마: tp_analysis
-- 포함: indicators_daily, sector_metrics_daily,
--       recommendations, signals, ml_predictions
-- =====================================================

SET search_path TO tp_analysis, public;

-- ----------------------------------------------------
-- indicators_daily : 일봉 기준 기술적 지표 캐시
--   와이드 컬럼(MA/RSI/MACD/BB/OBV/VWAP/Stoch/ATR)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_analysis.indicators_daily (
    stock_id        BIGINT          NOT NULL,
    trade_date      DATE            NOT NULL,
    -- 이동평균
    ma5             NUMERIC(20, 4)  NULL,
    ma20            NUMERIC(20, 4)  NULL,
    ma60            NUMERIC(20, 4)  NULL,
    ma120           NUMERIC(20, 4)  NULL,
    -- RSI(14)
    rsi14           NUMERIC(10, 4)  NULL,
    -- MACD (12/26/9)
    macd            NUMERIC(20, 4)  NULL,
    macd_signal     NUMERIC(20, 4)  NULL,
    macd_hist       NUMERIC(20, 4)  NULL,
    -- Bollinger (20, 2)
    bb_mid          NUMERIC(20, 4)  NULL,
    bb_upper        NUMERIC(20, 4)  NULL,
    bb_lower        NUMERIC(20, 4)  NULL,
    -- OBV (누적)
    obv             NUMERIC(20, 4)  NULL,
    -- VWAP (당일 누적)
    vwap            NUMERIC(20, 4)  NULL,
    -- Stochastic (14/3/3)
    stoch_k         NUMERIC(10, 4)  NULL,
    stoch_d         NUMERIC(10, 4)  NULL,
    -- ATR(14) - 변동성 게이트 사용
    atr14           NUMERIC(20, 4)  NULL,
    computed_at     TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_indicators_daily      PRIMARY KEY (stock_id, trade_date),
    CONSTRAINT fk_indicators_daily_stock FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id) ON DELETE CASCADE
);
COMMENT ON TABLE tp_analysis.indicators_daily IS '일봉 기준 기술적 지표 캐시 (5년 보관)';

-- ----------------------------------------------------
-- sector_metrics_daily : 섹터별 일별 등락/자금흐름/상관
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_analysis.sector_metrics_daily (
    sector_id       BIGINT          NOT NULL,
    trade_date      DATE            NOT NULL,
    change_pct      NUMERIC(10, 4)  NULL,
    volume_amount   NUMERIC(20, 4)  NULL,
    inflow_amount   NUMERIC(20, 4)  NULL,                                    -- 자금 유입
    outflow_amount  NUMERIC(20, 4)  NULL,                                    -- 자금 유출
    net_flow        NUMERIC(20, 4)  NULL,                                    -- 순매수
    correlation     JSONB           NULL,                                    -- 타 섹터와의 상관계수 (롤링 30D)
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_sector_metrics_daily      PRIMARY KEY (sector_id, trade_date),
    CONSTRAINT fk_sector_metrics_daily_sec  FOREIGN KEY (sector_id) REFERENCES tp_market.sectors(id) ON DELETE CASCADE
);
COMMENT ON TABLE tp_analysis.sector_metrics_daily IS '섹터별 일별 지표 (히트맵/자금흐름 캐시)';

-- ----------------------------------------------------
-- recommendations : 일별 추천주 (전략 × 종목 × 일자)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_analysis.recommendations (
    id              BIGSERIAL       PRIMARY KEY,
    stock_id        BIGINT          NOT NULL,
    strategy_id     BIGINT          NULL,                                    -- 시스템 전략 기반이면 NULL 허용
    trade_date      DATE            NOT NULL,
    score           NUMERIC(10, 4)  NOT NULL,                                -- 0~100
    reason_code     VARCHAR(50)     NULL,                                    -- 룰 코드 (예: RSI_OVERSOLD)
    reason_text     TEXT            NULL,                                    -- 사람이 읽는 사유
    features        JSONB           NOT NULL DEFAULT '{}'::jsonb,            -- 산출 시점 피처 스냅샷
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_reco_stock_id FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id) ON DELETE CASCADE,
    CONSTRAINT ck_reco_score    CHECK (score >= 0 AND score <= 100)
);
COMMENT ON TABLE tp_analysis.recommendations IS '일별 추천 종목 (1년 보관)';

-- ----------------------------------------------------
-- signals : 사용자별 매매 시그널
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_analysis.signals (
    id              BIGSERIAL       PRIMARY KEY,
    public_id       UUID            NOT NULL DEFAULT gen_random_uuid(),
    user_id         BIGINT          NOT NULL,
    strategy_id     BIGINT          NOT NULL,
    stock_id        BIGINT          NOT NULL,
    action          VARCHAR(10)     NOT NULL,                                -- BUY/SELL
    confidence      VARCHAR(10)     NOT NULL DEFAULT 'MID',                  -- HIGH/MID/LOW
    trigger_price   NUMERIC(20, 4)  NULL,
    status          VARCHAR(20)     NOT NULL DEFAULT 'ACTIVE',               -- ACTIVE/EXECUTED/IGNORED/EXPIRED
    condition_trace JSONB           NOT NULL DEFAULT '{}'::jsonb,            -- 충족 조건 트레이스
    generated_at    TIMESTAMPTZ     NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ     NULL,
    ignored_at      TIMESTAMPTZ     NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT uq_signals_public_id     UNIQUE (public_id),
    CONSTRAINT fk_signals_user_id       FOREIGN KEY (user_id)  REFERENCES tp_user.users(id)         ON DELETE CASCADE,
    CONSTRAINT fk_signals_stock_id      FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id)      ON DELETE CASCADE,
    CONSTRAINT ck_signals_action        CHECK (action IN ('BUY','SELL')),
    CONSTRAINT ck_signals_confidence    CHECK (confidence IN ('HIGH','MID','LOW')),
    CONSTRAINT ck_signals_status        CHECK (status IN ('ACTIVE','EXECUTED','IGNORED','EXPIRED'))
);
COMMENT ON TABLE tp_analysis.signals IS '매매 시그널 (2년 보관)';

CREATE TRIGGER trg_signals_updated_at
    BEFORE UPDATE ON tp_analysis.signals
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- ml_predictions : LSTM 단기 예측
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_analysis.ml_predictions (
    id              BIGSERIAL       PRIMARY KEY,
    stock_id        BIGINT          NOT NULL,
    base_date       DATE            NOT NULL,                                -- 예측 기준일
    horizon         SMALLINT        NOT NULL,                                -- 1~5 영업일 후
    pred_mean       NUMERIC(20, 4)  NOT NULL,
    pred_lower      NUMERIC(20, 4)  NOT NULL,
    pred_upper      NUMERIC(20, 4)  NOT NULL,
    model_version   VARCHAR(50)     NOT NULL,
    mape            NUMERIC(10, 4)  NULL,                                    -- 모델 평가지표(검증 시)
    direction_acc   NUMERIC(10, 4)  NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_ml_pred_stock_id  FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id) ON DELETE CASCADE,
    CONSTRAINT ck_ml_pred_horizon   CHECK (horizon BETWEEN 1 AND 5),
    CONSTRAINT ck_ml_pred_bounds    CHECK (pred_lower <= pred_mean AND pred_mean <= pred_upper)
);
COMMENT ON TABLE tp_analysis.ml_predictions IS 'LSTM 예측 결과 (1년 보관)';
