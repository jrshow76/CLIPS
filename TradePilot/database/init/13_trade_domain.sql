-- =====================================================
-- TradePilot - 매매 도메인 DDL
-- 파일: 13_trade_domain.sql
-- 스키마: tp_trade
-- 포함: strategies, strategy_rules, orders(파티션), fills(파티션),
--       positions, portfolios, daily_pnl, trade_limits, kill_switch_log
-- =====================================================

SET search_path TO tp_trade, public;

-- ----------------------------------------------------
-- strategies : 전략 정의
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.strategies (
    id              BIGSERIAL       PRIMARY KEY,
    public_id       UUID            NOT NULL DEFAULT gen_random_uuid(),
    user_id         BIGINT          NOT NULL,
    name            VARCHAR(100)    NOT NULL,
    description     TEXT            NULL,
    entry_rules     JSONB           NOT NULL DEFAULT '{}'::jsonb,            -- DSL: {"all":[{"indicator":"RSI","op":"<","value":30},...]}
    exit_rules      JSONB           NOT NULL DEFAULT '{}'::jsonb,
    universe        JSONB           NOT NULL DEFAULT '[]'::jsonb,            -- 종목 유니버스 정의
    limits          JSONB           NOT NULL DEFAULT '{}'::jsonb,            -- 전략별 한도(전체 한도와 별개)
    active          BOOLEAN         NOT NULL DEFAULT FALSE,
    activated_at    TIMESTAMPTZ     NULL,
    deactivated_at  TIMESTAMPTZ     NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ     NULL,
    CONSTRAINT uq_strategies_public_id UNIQUE (public_id),
    CONSTRAINT fk_strategies_user_id   FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE
);
COMMENT ON TABLE tp_trade.strategies IS '사용자 전략 정의 (소프트 삭제)';

CREATE TRIGGER trg_strategies_updated_at
    BEFORE UPDATE ON tp_trade.strategies
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- signals.strategy_id FK 추가 (12_analysis_domain에서 미완성)
ALTER TABLE tp_analysis.signals
    ADD CONSTRAINT fk_signals_strategy_id
    FOREIGN KEY (strategy_id) REFERENCES tp_trade.strategies(id) ON DELETE CASCADE;

-- recommendations.strategy_id FK 추가
ALTER TABLE tp_analysis.recommendations
    ADD CONSTRAINT fk_reco_strategy_id
    FOREIGN KEY (strategy_id) REFERENCES tp_trade.strategies(id) ON DELETE SET NULL;

-- ----------------------------------------------------
-- strategy_rules : 룰 분해 저장(검색/통계 가속용, JSONB 보조)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.strategy_rules (
    id              BIGSERIAL       PRIMARY KEY,
    strategy_id     BIGINT          NOT NULL,
    rule_type       VARCHAR(10)     NOT NULL,                                -- ENTRY/EXIT
    indicator       VARCHAR(50)     NOT NULL,                                -- RSI/MACD/MA/VOLUME 등
    op              VARCHAR(10)     NOT NULL,                                -- <, >, <=, >=, =, CROSS_UP, CROSS_DOWN
    value           NUMERIC(20, 4)  NULL,
    priority        INTEGER         NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_strategy_rules_strategy FOREIGN KEY (strategy_id) REFERENCES tp_trade.strategies(id) ON DELETE CASCADE,
    CONSTRAINT ck_strategy_rules_type     CHECK (rule_type IN ('ENTRY','EXIT'))
);
COMMENT ON TABLE tp_trade.strategy_rules IS '전략 룰 정규화(보조 검색용)';

-- ----------------------------------------------------
-- orders : 주문 (월별 RANGE 파티셔닝)
--   자식 파티션은 21_partitioning.sql에서 생성
--   PK는 (id, ordered_at) 복합 필요 (파티션 키 포함)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.orders (
    id                  BIGSERIAL       NOT NULL,
    public_id           UUID            NOT NULL DEFAULT gen_random_uuid(),
    user_id             BIGINT          NULL,                                -- 익명화 시 NULL 가능
    strategy_id         BIGINT          NULL,                                -- 전략 삭제 시 NULL
    signal_id           BIGINT          NULL,                                -- 시그널 삭제 시 NULL
    stock_id            BIGINT          NOT NULL,
    trade_mode          VARCHAR(10)     NOT NULL,                            -- SIM/LIVE
    side                VARCHAR(10)     NOT NULL,                            -- BUY/SELL
    order_type          VARCHAR(10)     NOT NULL,                            -- MARKET/LIMIT
    qty                 NUMERIC(20, 4)  NOT NULL,
    price               NUMERIC(20, 4)  NULL,                                -- 시장가는 NULL
    status              VARCHAR(20)     NOT NULL DEFAULT 'NEW',              -- NEW/PARTIAL/FILLED/CANCELED/REJECTED/EXPIRED
    broker_order_no     VARCHAR(50)     NULL,                                -- 증권사 주문번호(LIVE 한정)
    idempotency_key     VARCHAR(64)     NULL,                                -- 멱등성 키(24h 윈도우)
    reject_reason       TEXT            NULL,
    ordered_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    filled_at           TIMESTAMPTZ     NULL,
    canceled_at         TIMESTAMPTZ     NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_orders            PRIMARY KEY (id, ordered_at),
    CONSTRAINT ck_orders_trade_mode CHECK (trade_mode IN ('SIM','LIVE')),
    CONSTRAINT ck_orders_side       CHECK (side IN ('BUY','SELL')),
    CONSTRAINT ck_orders_type       CHECK (order_type IN ('MARKET','LIMIT')),
    CONSTRAINT ck_orders_status     CHECK (status IN ('NEW','PARTIAL','FILLED','CANCELED','REJECTED','EXPIRED','PENDING')),
    CONSTRAINT ck_orders_qty        CHECK (qty > 0),
    CONSTRAINT ck_orders_limit_price CHECK (order_type <> 'LIMIT' OR price IS NOT NULL)
) PARTITION BY RANGE (ordered_at);
COMMENT ON TABLE tp_trade.orders IS '주문 (월별 RANGE 파티셔닝, 10년 보관)';

-- 부모에 FK도 선언 (자식 파티션에 자동 전파)
ALTER TABLE tp_trade.orders
    ADD CONSTRAINT fk_orders_user_id    FOREIGN KEY (user_id)     REFERENCES tp_user.users(id)         ON DELETE SET NULL,
    ADD CONSTRAINT fk_orders_strategy   FOREIGN KEY (strategy_id) REFERENCES tp_trade.strategies(id)   ON DELETE SET NULL,
    ADD CONSTRAINT fk_orders_signal_id  FOREIGN KEY (signal_id)   REFERENCES tp_analysis.signals(id)   ON DELETE SET NULL,
    ADD CONSTRAINT fk_orders_stock_id   FOREIGN KEY (stock_id)    REFERENCES tp_market.stocks(id)      ON DELETE RESTRICT;

-- 트리거(updated_at) - 파티션 부모에 선언
CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON tp_trade.orders
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- fills : 체결 (월별 RANGE 파티셔닝)
--   1주문 N체결 가능. PK는 (id, filled_at)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.fills (
    id              BIGSERIAL       NOT NULL,
    order_id        BIGINT          NOT NULL,
    user_id         BIGINT          NULL,                                    -- 익명화 가능
    stock_id        BIGINT          NOT NULL,
    trade_mode      VARCHAR(10)     NOT NULL,
    fill_qty        NUMERIC(20, 4)  NOT NULL,
    fill_price      NUMERIC(20, 4)  NOT NULL,
    fee             NUMERIC(20, 4)  NOT NULL DEFAULT 0,
    tax             NUMERIC(20, 4)  NOT NULL DEFAULT 0,
    slippage        NUMERIC(10, 4)  NULL,
    filled_at       TIMESTAMPTZ     NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_fills             PRIMARY KEY (id, filled_at),
    CONSTRAINT ck_fills_trade_mode  CHECK (trade_mode IN ('SIM','LIVE')),
    CONSTRAINT ck_fills_qty         CHECK (fill_qty > 0),
    CONSTRAINT ck_fills_price       CHECK (fill_price >= 0)
) PARTITION BY RANGE (filled_at);
COMMENT ON TABLE tp_trade.fills IS '체결 (월별 RANGE 파티셔닝, 10년 보관)';

-- FK 추가 (파티션 부모)
-- 주의: PG에서 파티션 부모↔파티션 부모 간 FK는 PG12+에서 지원
ALTER TABLE tp_trade.fills
    ADD CONSTRAINT fk_fills_user_id  FOREIGN KEY (user_id)  REFERENCES tp_user.users(id)    ON DELETE SET NULL,
    ADD CONSTRAINT fk_fills_stock_id FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id) ON DELETE RESTRICT;
-- orders ↔ fills FK는 파티션-파티션 참조 제약 한계로 애플리케이션 레벨 + 트리거로 보완 권장

-- ----------------------------------------------------
-- positions : 현재 보유 포지션
--   사용자 × 종목 × 모드 단일 행
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.positions (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         BIGINT          NOT NULL,
    stock_id        BIGINT          NOT NULL,
    trade_mode      VARCHAR(10)     NOT NULL,
    qty             NUMERIC(20, 4)  NOT NULL DEFAULT 0,
    avg_price       NUMERIC(20, 4)  NOT NULL DEFAULT 0,
    realized_pnl    NUMERIC(20, 4)  NOT NULL DEFAULT 0,                      -- 누적 실현 손익
    opened_at       TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT uq_positions_user_stock_mode UNIQUE (user_id, stock_id, trade_mode),
    CONSTRAINT fk_positions_user_id  FOREIGN KEY (user_id)  REFERENCES tp_user.users(id)    ON DELETE CASCADE,
    CONSTRAINT fk_positions_stock_id FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id) ON DELETE RESTRICT,
    CONSTRAINT ck_positions_mode     CHECK (trade_mode IN ('SIM','LIVE')),
    CONSTRAINT ck_positions_qty      CHECK (qty >= 0)
);
COMMENT ON TABLE tp_trade.positions IS '현재 보유 포지션 (사용자×종목×모드 1행)';

CREATE TRIGGER trg_positions_updated_at
    BEFORE UPDATE ON tp_trade.positions
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- portfolios : 일별 자산 스냅샷
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.portfolios (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         BIGINT          NOT NULL,
    trade_mode      VARCHAR(10)     NOT NULL,
    cash            NUMERIC(20, 4)  NOT NULL DEFAULT 0,
    equity          NUMERIC(20, 4)  NOT NULL DEFAULT 0,                      -- 평가금액(보유종목)
    total_value     NUMERIC(20, 4)  NOT NULL DEFAULT 0,                      -- cash + equity
    snapshot_at     TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_portfolios_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE,
    CONSTRAINT ck_portfolios_mode    CHECK (trade_mode IN ('SIM','LIVE'))
);
COMMENT ON TABLE tp_trade.portfolios IS '일별 자산 스냅샷 (리포트 가속)';

-- ----------------------------------------------------
-- daily_pnl : 일별 손익 집계
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.daily_pnl (
    user_id             BIGINT          NOT NULL,
    trade_date          DATE            NOT NULL,
    trade_mode          VARCHAR(10)     NOT NULL,
    realized_pnl        NUMERIC(20, 4)  NOT NULL DEFAULT 0,
    unrealized_pnl      NUMERIC(20, 4)  NOT NULL DEFAULT 0,
    total_pnl           NUMERIC(20, 4)  NOT NULL DEFAULT 0,
    mdd                 NUMERIC(10, 4)  NULL,
    win_count           INTEGER         NOT NULL DEFAULT 0,
    loss_count          INTEGER         NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_daily_pnl         PRIMARY KEY (user_id, trade_date, trade_mode),
    CONSTRAINT fk_daily_pnl_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE,
    CONSTRAINT ck_daily_pnl_mode    CHECK (trade_mode IN ('SIM','LIVE'))
);
COMMENT ON TABLE tp_trade.daily_pnl IS '일별 손익 집계 (10년 보관)';

-- ----------------------------------------------------
-- trade_limits : 사용자 한도 설정 (1:1)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.trade_limits (
    user_id                 BIGINT          PRIMARY KEY,
    daily_buy_amount        NUMERIC(20, 4)  NOT NULL DEFAULT 5000000,        -- 기본 5,000,000
    daily_buy_count         INTEGER         NOT NULL DEFAULT 20,
    per_stock_amount        NUMERIC(20, 4)  NOT NULL DEFAULT 1000000,
    max_positions           INTEGER         NOT NULL DEFAULT 10,
    stop_loss_pct           NUMERIC(10, 4)  NOT NULL DEFAULT -3.0,           -- 음수
    take_profit_pct         NUMERIC(10, 4)  NOT NULL DEFAULT 5.0,
    daily_loss_limit_pct    NUMERIC(10, 4)  NOT NULL DEFAULT -5.0,
    single_order_max_qty    INTEGER         NOT NULL DEFAULT 1000,
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_trade_limits_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE,
    CONSTRAINT ck_trade_limits_daily_buy_amount CHECK (daily_buy_amount >= 0 AND daily_buy_amount <= 100000000),
    CONSTRAINT ck_trade_limits_daily_buy_count  CHECK (daily_buy_count   >= 0 AND daily_buy_count   <= 100),
    CONSTRAINT ck_trade_limits_per_stock        CHECK (per_stock_amount  >= 0 AND per_stock_amount  <= 30000000),
    CONSTRAINT ck_trade_limits_max_positions    CHECK (max_positions     >= 1 AND max_positions     <= 30),
    CONSTRAINT ck_trade_limits_stop_loss        CHECK (stop_loss_pct        >= -10.0 AND stop_loss_pct      <= 0),
    CONSTRAINT ck_trade_limits_take_profit      CHECK (take_profit_pct      >= 0     AND take_profit_pct    <= 30.0),
    CONSTRAINT ck_trade_limits_daily_loss       CHECK (daily_loss_limit_pct >= -15.0 AND daily_loss_limit_pct <= 0),
    CONSTRAINT ck_trade_limits_single_max       CHECK (single_order_max_qty >= 1     AND single_order_max_qty <= 10000)
);
COMMENT ON TABLE tp_trade.trade_limits IS '사용자별 매매 한도 (정책서 15_trading_policy 3.1)';

CREATE TRIGGER trg_trade_limits_updated_at
    BEFORE UPDATE ON tp_trade.trade_limits
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- kill_switch_log : 비상정지 이력
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.kill_switch_log (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         BIGINT          NOT NULL,
    trigger_type    VARCHAR(30)     NOT NULL,                                -- USER/DAILY_LOSS/CREON_DISCONNECT/SYSTEM/STOP_LOSS
    reason          TEXT            NULL,
    canceled_count  INTEGER         NOT NULL DEFAULT 0,
    failed_count    INTEGER         NOT NULL DEFAULT 0,
    detail          JSONB           NOT NULL DEFAULT '{}'::jsonb,
    triggered_at    TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_kill_switch_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE,
    CONSTRAINT ck_kill_switch_trigger CHECK (trigger_type IN ('USER','DAILY_LOSS','CREON_DISCONNECT','SYSTEM','STOP_LOSS','MAINTENANCE'))
);
COMMENT ON TABLE tp_trade.kill_switch_log IS '비상정지(Kill Switch) 이력 (영구 보관)';
