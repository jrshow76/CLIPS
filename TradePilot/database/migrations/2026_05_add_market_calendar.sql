-- =====================================================
-- TradePilot - 시장 캘린더(휴장일) 테이블 신규 생성
-- 파일: 2026_05_add_market_calendar.sql
-- 스키마: tp_market
-- 설명: KRX 휴장일 데이터를 영구 저장하여 모든 모듈에서
--       단일 소스로 조회한다. pykrx 자동 동기화 + 운영자 수동 입력 모두 지원.
-- 적용일: 2026-05-13
-- =====================================================

SET search_path TO tp_market, public;

-- ----------------------------------------------------
-- market_calendar : 시장 휴장일
--   - holiday_date: 휴장일(UNIQUE, 시장 + 일자 기준 중복 방지는 (market, holiday_date)로 보강)
--   - holiday_type: REGULAR(법정공휴일/정기) / TEMPORARY(임시휴장) / SUBSTITUTE(대체공휴일)
--   - market: 확장 대비 (KRX/NYSE 등). 현 시점 KRX 만 사용.
--   - source: 데이터 출처(pykrx/manual/seed). 자동/수동 구분.
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_market.market_calendar (
    id              BIGSERIAL       PRIMARY KEY,
    holiday_date    DATE            NOT NULL,
    holiday_name    VARCHAR(100)    NOT NULL,                                  -- 신정/설날/추석 등
    holiday_type    VARCHAR(20)     NOT NULL DEFAULT 'REGULAR',                -- REGULAR/TEMPORARY/SUBSTITUTE
    market          VARCHAR(10)     NOT NULL DEFAULT 'KRX',                    -- 확장 대비 (KRX/NYSE 등)
    description     TEXT            NULL,
    source          VARCHAR(20)     NOT NULL DEFAULT 'pykrx',                  -- pykrx/manual/seed
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT uq_market_calendar_market_date UNIQUE (market, holiday_date),
    CONSTRAINT ck_market_calendar_type CHECK (holiday_type IN ('REGULAR','TEMPORARY','SUBSTITUTE')),
    CONSTRAINT ck_market_calendar_source CHECK (source IN ('pykrx','manual','seed'))
);
COMMENT ON TABLE tp_market.market_calendar IS '시장 휴장일 캘린더 (KRX 자동 동기화 + 운영자 수동 입력)';
COMMENT ON COLUMN tp_market.market_calendar.holiday_type IS 'REGULAR: 법정/정기, TEMPORARY: 임시휴장, SUBSTITUTE: 대체공휴일';
COMMENT ON COLUMN tp_market.market_calendar.source IS 'pykrx: 자동 동기화, manual: 운영자 수동, seed: 초기 시드';

-- 단일 컬럼 holiday_date에도 UNIQUE를 부여한다(요구사항). market 확장이 필요한 시점에는 제거 검토.
CREATE UNIQUE INDEX IF NOT EXISTS uq_market_calendar_holiday_date
    ON tp_market.market_calendar (holiday_date);

-- 조회 인덱스
CREATE INDEX IF NOT EXISTS idx_market_calendar_market_date
    ON tp_market.market_calendar (market, holiday_date);

-- updated_at 자동 갱신
DROP TRIGGER IF EXISTS trg_market_calendar_updated_at ON tp_market.market_calendar;
CREATE TRIGGER trg_market_calendar_updated_at
    BEFORE UPDATE ON tp_market.market_calendar
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


-- =====================================================
-- 시드 데이터: 2024 ~ 2026 한국 휴장일
-- 출처: 한국거래소(KRX) 공시 일정 (관공서 공휴일 + 임시휴장)
--   - 2024: 확정
--   - 2025: 확정
--   - 2026: 잠정 (sync_from_krx 로 정정 가능)
-- 모든 행은 source='seed' 로 등록.
-- =====================================================
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

    -- ---------- 2026년 (잠정 - KRX 확정 공시 시 sync_from_krx 로 정정) ----------
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

-- =====================================================
-- 시드 결과 확인 쿼리(코멘트)
-- =====================================================
-- SELECT EXTRACT(YEAR FROM holiday_date)::INT AS year, COUNT(*) AS holidays
--   FROM tp_market.market_calendar
--   WHERE market = 'KRX'
--   GROUP BY year
--   ORDER BY year;
