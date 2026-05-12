-- =====================================================
-- TradePilot - 시장 데이터 도메인 DDL
-- 파일: 11_market_domain.sql
-- 스키마: tp_market
-- 포함: stocks, sectors, stock_sectors, market_index,
--       market_index_daily, price_daily, price_minute(파티션),
--       corporate_actions
-- =====================================================

SET search_path TO tp_market, public;

-- ----------------------------------------------------
-- stocks : 종목 마스터
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_market.stocks (
    id              BIGSERIAL       PRIMARY KEY,
    code            VARCHAR(6)      NOT NULL,                                -- 6자리 종목코드
    name            VARCHAR(100)    NOT NULL,
    market          VARCHAR(10)     NOT NULL,                                -- KOSPI/KOSDAQ
    status          VARCHAR(20)     NOT NULL DEFAULT 'LISTED',               -- LISTED/SUSPENDED/DELISTED
    listing_shares  BIGINT          NULL,                                    -- 상장주식수
    market_cap      BIGINT          NULL,                                    -- 시가총액(원)
    par_value       INTEGER         NULL,                                    -- 액면가
    listed_at       DATE            NULL,
    delisted_at     DATE            NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT uq_stocks_code        UNIQUE (code),
    CONSTRAINT ck_stocks_code_format CHECK (code ~ '^[0-9]{6}$'),
    CONSTRAINT ck_stocks_market      CHECK (market IN ('KOSPI','KOSDAQ','KONEX','ETF')),
    CONSTRAINT ck_stocks_status      CHECK (status IN ('LISTED','SUSPENDED','DELISTED'))
);
COMMENT ON TABLE tp_market.stocks IS '종목 마스터 (KRX 6자리 코드 기준)';

CREATE TRIGGER trg_stocks_updated_at
    BEFORE UPDATE ON tp_market.stocks
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- user_favorites 외래키 (10_user_domain.sql에서 미완성)
-- ----------------------------------------------------
ALTER TABLE tp_user.user_favorites
    ADD CONSTRAINT fk_user_favorites_stock_id
    FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id) ON DELETE RESTRICT;

-- ----------------------------------------------------
-- sectors : 섹터/업종 마스터
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_market.sectors (
    id              BIGSERIAL       PRIMARY KEY,
    code            VARCHAR(20)     NOT NULL,                                -- KRX 업종코드 또는 GICS
    name            VARCHAR(100)    NOT NULL,
    parent_code     VARCHAR(20)     NULL,                                    -- 상위 섹터
    sort_order      INTEGER         NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT uq_sectors_code UNIQUE (code)
);
COMMENT ON TABLE tp_market.sectors IS '섹터/업종 마스터';

CREATE TRIGGER trg_sectors_updated_at
    BEFORE UPDATE ON tp_market.sectors
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- stock_sectors : 종목-섹터 M:N 매핑
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_market.stock_sectors (
    stock_id    BIGINT          NOT NULL,
    sector_id   BIGINT          NOT NULL,
    is_primary  BOOLEAN         NOT NULL DEFAULT FALSE,                      -- 대표 섹터 여부
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_stock_sectors          PRIMARY KEY (stock_id, sector_id),
    CONSTRAINT fk_stock_sectors_stock_id FOREIGN KEY (stock_id)  REFERENCES tp_market.stocks(id)  ON DELETE CASCADE,
    CONSTRAINT fk_stock_sectors_sector_id FOREIGN KEY (sector_id) REFERENCES tp_market.sectors(id) ON DELETE CASCADE
);
COMMENT ON TABLE tp_market.stock_sectors IS '종목-섹터 매핑 (다중 섹터 가능, is_primary=true가 대표)';

-- ----------------------------------------------------
-- corporate_actions : 기업액션(무상/유상증자, 액면분할, 배당)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_market.corporate_actions (
    id              BIGSERIAL       PRIMARY KEY,
    stock_id        BIGINT          NOT NULL,
    action_type     VARCHAR(20)     NOT NULL,                                -- SPLIT/MERGE/DIV/BONUS/RIGHTS_OFFERING
    effective_date  DATE            NOT NULL,
    ratio           NUMERIC(20, 8)  NULL,                                    -- 분할/병합 비율
    cash_amount     NUMERIC(20, 4)  NULL,                                    -- 배당금
    detail          JSONB           NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_corp_action_stock_id  FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id) ON DELETE CASCADE,
    CONSTRAINT ck_corp_action_type      CHECK (action_type IN ('SPLIT','MERGE','DIV','BONUS','RIGHTS_OFFERING','DELIST'))
);
COMMENT ON TABLE tp_market.corporate_actions IS '기업 액션 (adj_close 산출 근거)';

-- ----------------------------------------------------
-- price_daily : 일봉 (단일 테이블, UNIQUE 보장)
--   5년 보관, 미파티셔닝(예상 5천만 행 이하)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_market.price_daily (
    stock_id        BIGINT          NOT NULL,
    trade_date      DATE            NOT NULL,
    open            NUMERIC(20, 4)  NOT NULL,
    high            NUMERIC(20, 4)  NOT NULL,
    low             NUMERIC(20, 4)  NOT NULL,
    close           NUMERIC(20, 4)  NOT NULL,
    volume          BIGINT          NOT NULL DEFAULT 0,
    volume_amount   NUMERIC(20, 4)  NOT NULL DEFAULT 0,                      -- 거래대금
    change_pct      NUMERIC(10, 4)  NULL,                                    -- 전일대비 등락률
    adj_close       NUMERIC(20, 4)  NULL,                                    -- 수정종가
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_price_daily          PRIMARY KEY (stock_id, trade_date),
    CONSTRAINT fk_price_daily_stock_id FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id) ON DELETE CASCADE,
    CONSTRAINT ck_price_daily_ohlc     CHECK (low <= open AND low <= close AND high >= open AND high >= close)
);
COMMENT ON TABLE tp_market.price_daily IS '일봉 (stock_id, trade_date) UNIQUE. 5년 보관';

-- ----------------------------------------------------
-- price_minute : 분봉 (월별 RANGE 파티셔닝)
--   interval_min : 1, 5, 15, 30 (분 단위)
--   파티션 자식 테이블은 21_partitioning.sql에서 생성
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_market.price_minute (
    stock_id        BIGINT          NOT NULL,
    ts              TIMESTAMPTZ     NOT NULL,
    interval_min    SMALLINT        NOT NULL,                                -- 1/5/15/30
    open            NUMERIC(20, 4)  NOT NULL,
    high            NUMERIC(20, 4)  NOT NULL,
    low             NUMERIC(20, 4)  NOT NULL,
    close           NUMERIC(20, 4)  NOT NULL,
    volume          BIGINT          NOT NULL DEFAULT 0,
    volume_amount   NUMERIC(20, 4)  NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_price_minute      PRIMARY KEY (stock_id, ts, interval_min),
    CONSTRAINT ck_price_minute_interval CHECK (interval_min IN (1,5,15,30))
) PARTITION BY RANGE (ts);
COMMENT ON TABLE tp_market.price_minute IS '분봉 (월별 RANGE 파티셔닝). 1분봉 1년, 5분 이상 5년 보관';

-- 부모 테이블에 FK도 선언 → 자식에 자동 전파(PG11+)
ALTER TABLE tp_market.price_minute
    ADD CONSTRAINT fk_price_minute_stock_id
    FOREIGN KEY (stock_id) REFERENCES tp_market.stocks(id) ON DELETE CASCADE;

-- ----------------------------------------------------
-- market_index : 시장 지수 마스터 (KOSPI/KOSDAQ)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_market.market_index (
    id          BIGSERIAL       PRIMARY KEY,
    code        VARCHAR(20)     NOT NULL,                                    -- KOSPI/KOSDAQ/KOSPI200
    name        VARCHAR(50)     NOT NULL,
    market      VARCHAR(10)     NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT uq_market_index_code UNIQUE (code)
);
COMMENT ON TABLE tp_market.market_index IS '시장 지수 마스터';

-- ----------------------------------------------------
-- market_index_daily : 지수 일봉
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_market.market_index_daily (
    index_id    BIGINT          NOT NULL,
    trade_date  DATE            NOT NULL,
    open        NUMERIC(20, 4)  NOT NULL,
    high        NUMERIC(20, 4)  NOT NULL,
    low         NUMERIC(20, 4)  NOT NULL,
    close       NUMERIC(20, 4)  NOT NULL,
    volume      BIGINT          NOT NULL DEFAULT 0,
    change_pct  NUMERIC(10, 4)  NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_market_index_daily        PRIMARY KEY (index_id, trade_date),
    CONSTRAINT fk_market_index_daily_index  FOREIGN KEY (index_id) REFERENCES tp_market.market_index(id) ON DELETE CASCADE
);
COMMENT ON TABLE tp_market.market_index_daily IS '지수 일봉 (KOSPI/KOSDAQ)';
