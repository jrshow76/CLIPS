-- =====================================================
-- TradePilot - 머터리얼라이즈드 뷰 추가 마이그레이션
-- 파일: 2026_05_add_materialized_views.sql
-- 작성자: DBA
-- 작성일: 2026-05-14
--
-- 목적:
--   집계성 화면(대시보드/업종 분석)에서 매 요청마다 집계 SQL을
--   재실행하는 비용을 줄이고 응답시간을 안정화한다.
--
-- 갱신 방침:
--   - 운영 초기에는 매일 1회(장 마감 후) REFRESH MATERIALIZED VIEW CONCURRENTLY
--   - 사용량 증가 시 트리거 기반 incremental 또는 pg_ivm 도입 검토
--   - REFRESH CONCURRENTLY 는 UNIQUE 인덱스 필수 → 각 MV에 UNIQUE 인덱스 정의
--
-- Celery Beat 등록 가이드 (코드는 별도 PR로, 본 SQL에는 미포함):
--   tp_market.mv_sector_daily_summary  → 매일 17:00 KST
--   tp_analysis.mv_indicator_summary   → 매일 17:30 KST (지표 산출 후)
--   tp_trade.mv_user_pnl_summary       → 매일 18:00 KST (PnL 산출 후)
--
--   예시(scripts/db/refresh_mvs.sql):
--     REFRESH MATERIALIZED VIEW CONCURRENTLY tp_market.mv_sector_daily_summary;
--     REFRESH MATERIALIZED VIEW CONCURRENTLY tp_analysis.mv_indicator_summary;
--     REFRESH MATERIALIZED VIEW CONCURRENTLY tp_trade.mv_user_pnl_summary;
-- =====================================================

-- =====================================================
-- 1. mv_sector_daily_summary
--    섹터별 일일 등락/자금흐름 + 직전 영업일 비교
--    화면: 업종 분석 메인 / 섹터 히트맵
--    대체 쿼리: M-12 (N+1 패턴 제거)
-- =====================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS tp_market.mv_sector_daily_summary AS
WITH latest_per_sector AS (
    SELECT
        sector_id,
        MAX(trade_date) AS latest_date
    FROM tp_analysis.sector_metrics_daily
    GROUP BY sector_id
),
latest_row AS (
    SELECT
        m.sector_id,
        m.trade_date    AS latest_date,
        m.change_pct    AS latest_change_pct,
        m.volume_amount AS latest_volume_amount,
        m.inflow_amount,
        m.outflow_amount,
        m.net_flow
    FROM tp_analysis.sector_metrics_daily m
    JOIN latest_per_sector l
      ON l.sector_id = m.sector_id
     AND l.latest_date = m.trade_date
),
prev_row AS (
    -- 직전 영업일 비교용
    SELECT
        m.sector_id,
        m.trade_date,
        m.change_pct AS prev_change_pct,
        ROW_NUMBER() OVER (PARTITION BY m.sector_id ORDER BY m.trade_date DESC) AS rn
    FROM tp_analysis.sector_metrics_daily m
)
SELECT
    s.id              AS sector_id,
    s.code            AS sector_code,
    s.name            AS sector_name,
    s.parent_code,
    s.sort_order,
    lr.latest_date,
    lr.latest_change_pct,
    pr.prev_change_pct,
    lr.latest_volume_amount,
    lr.inflow_amount,
    lr.outflow_amount,
    lr.net_flow,
    -- 5일 평균 등락률(보조 지표)
    (
        SELECT AVG(m5.change_pct)
        FROM tp_analysis.sector_metrics_daily m5
        WHERE m5.sector_id = s.id
          AND m5.trade_date BETWEEN lr.latest_date - INTERVAL '7 days' AND lr.latest_date
    )::numeric(10,4) AS avg5d_change_pct
FROM tp_market.sectors s
LEFT JOIN latest_row lr ON lr.sector_id = s.id
LEFT JOIN prev_row pr ON pr.sector_id = s.id AND pr.rn = 2
WITH NO DATA;
COMMENT ON MATERIALIZED VIEW tp_market.mv_sector_daily_summary IS
    '섹터별 일일 등락/자금흐름 + 5일 평균 등락 요약. REFRESH: 매일 17:00 KST';

-- REFRESH CONCURRENTLY 위해 UNIQUE 인덱스 필수
CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_sector_daily_summary
    ON tp_market.mv_sector_daily_summary (sector_id);

-- 정렬 가속(히트맵 등락 순)
CREATE INDEX IF NOT EXISTS idx_mv_sector_daily_summary_change
    ON tp_market.mv_sector_daily_summary (latest_change_pct DESC NULLS LAST);

-- 초기 적재 (운영 적용 시 1회 실행):
-- REFRESH MATERIALIZED VIEW tp_market.mv_sector_daily_summary;


-- =====================================================
-- 2. mv_indicator_summary
--    종목별 최신 지표 스냅샷
--    화면: 종목 검색/필터링(과매도/과매수 등 빠른 필터)
--    A-15/A-16의 정적 partial 인덱스로 처리되는 케이스 외,
--    "최신 1행"만 필요한 화면용
-- =====================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS tp_analysis.mv_indicator_summary AS
WITH latest_per_stock AS (
    SELECT
        stock_id,
        MAX(trade_date) AS latest_date
    FROM tp_analysis.indicators_daily
    GROUP BY stock_id
)
SELECT
    i.stock_id,
    s.code,
    s.name,
    s.market,
    i.trade_date              AS as_of_date,
    i.ma5,
    i.ma20,
    i.ma60,
    i.ma120,
    i.rsi14,
    i.macd,
    i.macd_signal,
    i.macd_hist,
    i.bb_upper,
    i.bb_mid,
    i.bb_lower,
    i.atr14,
    -- 파생 플래그: 화면 필터용
    (i.rsi14 IS NOT NULL AND i.rsi14 < 30) AS is_oversold,
    (i.rsi14 IS NOT NULL AND i.rsi14 > 70) AS is_overbought,
    (i.macd IS NOT NULL AND i.macd_signal IS NOT NULL AND i.macd > i.macd_signal) AS macd_golden,
    (i.ma5  IS NOT NULL AND i.ma20 IS NOT NULL AND i.ma5  > i.ma20) AS ma5_above_ma20
FROM tp_analysis.indicators_daily i
JOIN latest_per_stock l
  ON l.stock_id = i.stock_id
 AND l.latest_date = i.trade_date
JOIN tp_market.stocks s ON s.id = i.stock_id
WHERE s.status = 'LISTED'
WITH NO DATA;
COMMENT ON MATERIALIZED VIEW tp_analysis.mv_indicator_summary IS
    '종목별 최신 기술적 지표 스냅샷(LISTED 한정). REFRESH: 매일 17:30 KST';

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_indicator_summary
    ON tp_analysis.mv_indicator_summary (stock_id);

-- 화면 필터 가속
CREATE INDEX IF NOT EXISTS idx_mv_indicator_oversold
    ON tp_analysis.mv_indicator_summary (rsi14)
    WHERE is_oversold;
CREATE INDEX IF NOT EXISTS idx_mv_indicator_golden
    ON tp_analysis.mv_indicator_summary (as_of_date)
    WHERE macd_golden;
CREATE INDEX IF NOT EXISTS idx_mv_indicator_code
    ON tp_analysis.mv_indicator_summary (code);


-- =====================================================
-- 3. mv_user_pnl_summary
--    사용자별 누적 PnL / 승률 / MDD
--    화면: 대시보드 위젯, 마이페이지
--    대체 쿼리: T-17
-- =====================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS tp_trade.mv_user_pnl_summary AS
WITH agg AS (
    SELECT
        user_id,
        trade_mode,
        COUNT(*)                                    AS day_count,
        SUM(realized_pnl)                           AS sum_realized,
        SUM(unrealized_pnl)                         AS sum_unrealized,
        SUM(total_pnl)                              AS sum_total,
        SUM(win_count)                              AS sum_win,
        SUM(loss_count)                             AS sum_loss,
        MIN(mdd)                                    AS worst_mdd,            -- 음수가 작을수록 큼
        AVG(total_pnl)                              AS avg_daily_pnl,
        MAX(trade_date)                             AS last_trade_date
    FROM tp_trade.daily_pnl
    GROUP BY user_id, trade_mode
),
last30 AS (
    SELECT
        user_id,
        trade_mode,
        SUM(total_pnl)        AS pnl_30d,
        COUNT(*) FILTER (WHERE total_pnl > 0) AS win_30d,
        COUNT(*) FILTER (WHERE total_pnl < 0) AS loss_30d
    FROM tp_trade.daily_pnl
    WHERE trade_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY user_id, trade_mode
)
SELECT
    a.user_id,
    a.trade_mode,
    a.day_count,
    a.sum_realized,
    a.sum_unrealized,
    a.sum_total,
    a.sum_win,
    a.sum_loss,
    a.worst_mdd,
    a.avg_daily_pnl,
    a.last_trade_date,
    -- 승률(전체)
    CASE WHEN (a.sum_win + a.sum_loss) > 0
         THEN ROUND(100.0 * a.sum_win / (a.sum_win + a.sum_loss), 4)
         ELSE NULL
    END AS win_rate_pct,
    -- 최근 30일
    l30.pnl_30d,
    l30.win_30d,
    l30.loss_30d
FROM agg a
LEFT JOIN last30 l30
    ON l30.user_id = a.user_id AND l30.trade_mode = a.trade_mode
WITH NO DATA;
COMMENT ON MATERIALIZED VIEW tp_trade.mv_user_pnl_summary IS
    '사용자×모드별 누적 PnL/승률/MDD 요약. REFRESH: 매일 18:00 KST (PnL 산출 후)';

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_user_pnl_summary
    ON tp_trade.mv_user_pnl_summary (user_id, trade_mode);

-- 마이페이지 정렬(랭킹용 보조)
CREATE INDEX IF NOT EXISTS idx_mv_user_pnl_total
    ON tp_trade.mv_user_pnl_summary (sum_total DESC);


-- =====================================================
-- 4. 일괄 REFRESH 함수 (운영 편의)
-- =====================================================

CREATE OR REPLACE FUNCTION public.fn_refresh_materialized_views(p_concurrently BOOLEAN DEFAULT TRUE)
RETURNS TABLE(mv_name TEXT, refreshed_at TIMESTAMPTZ, duration_ms BIGINT) AS $$
DECLARE
    v_start TIMESTAMPTZ;
    v_sql   TEXT;
    v_mvs   TEXT[] := ARRAY[
        'tp_market.mv_sector_daily_summary',
        'tp_analysis.mv_indicator_summary',
        'tp_trade.mv_user_pnl_summary'
    ];
    v_mv    TEXT;
BEGIN
    FOREACH v_mv IN ARRAY v_mvs LOOP
        v_start := clock_timestamp();
        v_sql := format('REFRESH MATERIALIZED VIEW %s %s',
                         CASE WHEN p_concurrently THEN 'CONCURRENTLY' ELSE '' END,
                         v_mv);
        BEGIN
            EXECUTE v_sql;
        EXCEPTION WHEN OTHERS THEN
            -- CONCURRENTLY 가 실패하면(예: 데이터 미적재) 일반 REFRESH 시도
            EXECUTE format('REFRESH MATERIALIZED VIEW %s', v_mv);
        END;
        mv_name      := v_mv;
        refreshed_at := clock_timestamp();
        duration_ms  := EXTRACT(EPOCH FROM (clock_timestamp() - v_start))::BIGINT * 1000;
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION public.fn_refresh_materialized_views(BOOLEAN)
    IS '모든 MV를 일괄 REFRESH. p_concurrently=true(기본)는 CONCURRENTLY 시도.';


-- =====================================================
-- 초기 적재 가이드
-- =====================================================
-- 1) 첫 적재(데이터가 없으면 SKIP)
--    REFRESH MATERIALIZED VIEW tp_market.mv_sector_daily_summary;
--    REFRESH MATERIALIZED VIEW tp_analysis.mv_indicator_summary;
--    REFRESH MATERIALIZED VIEW tp_trade.mv_user_pnl_summary;
--
-- 2) 정기 REFRESH (Celery beat / cron)
--    psql -d $DATABASE_URL -c "SELECT * FROM public.fn_refresh_materialized_views(true);"
--
-- 3) 데이터 정합성 점검
--    SELECT COUNT(*) FROM tp_market.mv_sector_daily_summary;
--    SELECT COUNT(*) FROM tp_analysis.mv_indicator_summary;
--    SELECT COUNT(*) FROM tp_trade.mv_user_pnl_summary;
