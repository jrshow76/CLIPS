-- =====================================================
-- TradePilot - 시장 캘린더(휴장일) 초기화 시드
-- 파일: 16_calendar_seed.sql
-- 설명: 컨테이너 init 단계에서 실행. 마이그레이션과 동일한 시드를
--       idempotent 방식으로 적용한다(ON CONFLICT DO NOTHING).
--       마이그레이션 파일(database/migrations/2026_05_add_market_calendar.sql)과
--       데이터 일치를 유지한다.
-- =====================================================

SET search_path TO tp_market, public;

-- ----------------------------------------------------
-- market_calendar : 시장 휴장일 (init 단계 idempotent)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_market.market_calendar (
    id              BIGSERIAL       PRIMARY KEY,
    holiday_date    DATE            NOT NULL,
    holiday_name    VARCHAR(100)    NOT NULL,
    holiday_type    VARCHAR(20)     NOT NULL DEFAULT 'REGULAR',
    market          VARCHAR(10)     NOT NULL DEFAULT 'KRX',
    description     TEXT            NULL,
    source          VARCHAR(20)     NOT NULL DEFAULT 'pykrx',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT uq_market_calendar_market_date UNIQUE (market, holiday_date),
    CONSTRAINT ck_market_calendar_type CHECK (holiday_type IN ('REGULAR','TEMPORARY','SUBSTITUTE')),
    CONSTRAINT ck_market_calendar_source CHECK (source IN ('pykrx','manual','seed'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_market_calendar_holiday_date
    ON tp_market.market_calendar (holiday_date);
CREATE INDEX IF NOT EXISTS idx_market_calendar_market_date
    ON tp_market.market_calendar (market, holiday_date);

DROP TRIGGER IF EXISTS trg_market_calendar_updated_at ON tp_market.market_calendar;
CREATE TRIGGER trg_market_calendar_updated_at
    BEFORE UPDATE ON tp_market.market_calendar
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- 시드 데이터 (2024 ~ 2026)
-- ON CONFLICT DO NOTHING 으로 idempotent
-- ----------------------------------------------------
INSERT INTO tp_market.market_calendar (holiday_date, holiday_name, holiday_type, market, source) VALUES
    -- ---------- 2024년 ----------
    ('2024-01-01', '신정',                'REGULAR',    'KRX', 'seed'),
    ('2024-02-09', '설날 연휴',           'REGULAR',    'KRX', 'seed'),
    ('2024-02-12', '설날 대체공휴일',     'SUBSTITUTE', 'KRX', 'seed'),
    ('2024-03-01', '삼일절',              'REGULAR',    'KRX', 'seed'),
    ('2024-04-10', '국회의원선거일',      'TEMPORARY',  'KRX', 'seed'),
    ('2024-05-01', '근로자의 날',         'REGULAR',    'KRX', 'seed'),
    ('2024-05-06', '어린이날 대체공휴일', 'SUBSTITUTE', 'KRX', 'seed'),
    ('2024-05-15', '부처님오신날',        'REGULAR',    'KRX', 'seed'),
    ('2024-06-06', '현충일',              'REGULAR',    'KRX', 'seed'),
    ('2024-08-15', '광복절',              'REGULAR',    'KRX', 'seed'),
    ('2024-09-16', '추석 연휴',           'REGULAR',    'KRX', 'seed'),
    ('2024-09-17', '추석',                'REGULAR',    'KRX', 'seed'),
    ('2024-09-18', '추석 연휴',           'REGULAR',    'KRX', 'seed'),
    ('2024-10-01', '국군의 날(임시공휴일)', 'TEMPORARY','KRX', 'seed'),
    ('2024-10-03', '개천절',              'REGULAR',    'KRX', 'seed'),
    ('2024-10-09', '한글날',              'REGULAR',    'KRX', 'seed'),
    ('2024-12-25', '성탄절',              'REGULAR',    'KRX', 'seed'),
    ('2024-12-31', '연말 휴장일',         'REGULAR',    'KRX', 'seed'),

    -- ---------- 2025년 ----------
    ('2025-01-01', '신정',                'REGULAR',    'KRX', 'seed'),
    ('2025-01-28', '설날 연휴',           'REGULAR',    'KRX', 'seed'),
    ('2025-01-29', '설날',                'REGULAR',    'KRX', 'seed'),
    ('2025-01-30', '설날 연휴',           'REGULAR',    'KRX', 'seed'),
    ('2025-03-03', '삼일절 대체공휴일',   'SUBSTITUTE', 'KRX', 'seed'),
    ('2025-05-01', '근로자의 날',         'REGULAR',    'KRX', 'seed'),
    ('2025-05-05', '어린이날/부처님오신날', 'REGULAR',  'KRX', 'seed'),
    ('2025-05-06', '어린이날 대체공휴일', 'SUBSTITUTE', 'KRX', 'seed'),
    ('2025-06-03', '대통령선거일',        'TEMPORARY',  'KRX', 'seed'),
    ('2025-06-06', '현충일',              'REGULAR',    'KRX', 'seed'),
    ('2025-08-15', '광복절',              'REGULAR',    'KRX', 'seed'),
    ('2025-10-03', '개천절',              'REGULAR',    'KRX', 'seed'),
    ('2025-10-06', '추석 연휴',           'REGULAR',    'KRX', 'seed'),
    ('2025-10-07', '추석',                'REGULAR',    'KRX', 'seed'),
    ('2025-10-08', '추석 연휴',           'REGULAR',    'KRX', 'seed'),
    ('2025-10-09', '한글날',              'REGULAR',    'KRX', 'seed'),
    ('2025-12-25', '성탄절',              'REGULAR',    'KRX', 'seed'),
    ('2025-12-31', '연말 휴장일',         'REGULAR',    'KRX', 'seed'),

    -- ---------- 2026년 (잠정) ----------
    ('2026-01-01', '신정',                'REGULAR',    'KRX', 'seed'),
    ('2026-02-16', '설날 연휴',           'REGULAR',    'KRX', 'seed'),
    ('2026-02-17', '설날',                'REGULAR',    'KRX', 'seed'),
    ('2026-02-18', '설날 연휴',           'REGULAR',    'KRX', 'seed'),
    ('2026-03-02', '삼일절 대체공휴일',   'SUBSTITUTE', 'KRX', 'seed'),
    ('2026-05-01', '근로자의 날',         'REGULAR',    'KRX', 'seed'),
    ('2026-05-05', '어린이날',            'REGULAR',    'KRX', 'seed'),
    ('2026-05-25', '부처님오신날',        'REGULAR',    'KRX', 'seed'),
    ('2026-06-03', '지방선거일',          'TEMPORARY',  'KRX', 'seed'),
    ('2026-08-17', '광복절 대체공휴일',   'SUBSTITUTE', 'KRX', 'seed'),
    ('2026-09-24', '추석 연휴',           'REGULAR',    'KRX', 'seed'),
    ('2026-09-25', '추석',                'REGULAR',    'KRX', 'seed'),
    ('2026-10-05', '개천절 대체공휴일',   'SUBSTITUTE', 'KRX', 'seed'),
    ('2026-10-09', '한글날',              'REGULAR',    'KRX', 'seed'),
    ('2026-12-25', '성탄절',              'REGULAR',    'KRX', 'seed'),
    ('2026-12-31', '연말 휴장일',         'REGULAR',    'KRX', 'seed')
ON CONFLICT (market, holiday_date) DO NOTHING;
