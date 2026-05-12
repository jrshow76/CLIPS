-- =====================================================
-- TradePilot - 월별 RANGE 파티션 초기 생성
-- 파일: 21_partitioning.sql
-- 대상: price_minute, orders, fills, notifications, audit_order_history
-- 본 파일은 초기 파티션(현재~+3개월)만 생성한다.
-- 운영 중에는 scripts/db/create_partition.sh 가 매월 자동 생성한다.
-- =====================================================

-- 헬퍼: 파티션 생성용 PL/pgSQL 함수
-- 매월 1일~다음달 1일 RANGE로 자식 파티션 만들기
CREATE OR REPLACE FUNCTION public.fn_create_monthly_partition(
    p_parent_schema  TEXT,
    p_parent_table   TEXT,
    p_year           INT,
    p_month          INT
) RETURNS TEXT AS $$
DECLARE
    v_partition_name TEXT;
    v_start_date     DATE;
    v_end_date       DATE;
    v_sql            TEXT;
BEGIN
    v_partition_name := format('%s_y%sm%s',
        p_parent_table,
        p_year,
        lpad(p_month::TEXT, 2, '0'));
    v_start_date := make_date(p_year, p_month, 1);
    v_end_date   := (v_start_date + INTERVAL '1 month')::DATE;

    v_sql := format(
        'CREATE TABLE IF NOT EXISTS %I.%I PARTITION OF %I.%I FOR VALUES FROM (%L) TO (%L);',
        p_parent_schema, v_partition_name,
        p_parent_schema, p_parent_table,
        v_start_date, v_end_date
    );
    EXECUTE v_sql;
    RETURN v_partition_name;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION public.fn_create_monthly_partition(TEXT,TEXT,INT,INT)
    IS '월별 RANGE 파티션 자식 테이블 생성 헬퍼';

-- =====================================================
-- DEFAULT 파티션 (안전망)
--   부모 정의 시점에 미리 만들어두면 키 범위 미지정 데이터 유실 방지
-- =====================================================
CREATE TABLE IF NOT EXISTS tp_market.price_minute_default
    PARTITION OF tp_market.price_minute DEFAULT;

CREATE TABLE IF NOT EXISTS tp_trade.orders_default
    PARTITION OF tp_trade.orders DEFAULT;

CREATE TABLE IF NOT EXISTS tp_trade.fills_default
    PARTITION OF tp_trade.fills DEFAULT;

CREATE TABLE IF NOT EXISTS tp_notify.notifications_default
    PARTITION OF tp_notify.notifications DEFAULT;

CREATE TABLE IF NOT EXISTS tp_audit.audit_order_history_default
    PARTITION OF tp_audit.audit_order_history DEFAULT;

-- =====================================================
-- 초기 파티션: 2026-04 ~ 2026-08 (현재 시점 ±)
-- 운영 시에는 cron으로 매월 익월/익월+1 자동 생성
-- =====================================================
DO $$
DECLARE
    v_year   INT;
    v_month  INT;
    v_target DATE;
BEGIN
    -- 5개월치(이번 달 -1 ~ +3) 사전 생성
    FOR i IN -1..3 LOOP
        v_target := (date_trunc('month', CURRENT_DATE) + (i || ' months')::INTERVAL)::DATE;
        v_year  := EXTRACT(YEAR  FROM v_target)::INT;
        v_month := EXTRACT(MONTH FROM v_target)::INT;

        PERFORM public.fn_create_monthly_partition('tp_market', 'price_minute',         v_year, v_month);
        PERFORM public.fn_create_monthly_partition('tp_trade',  'orders',               v_year, v_month);
        PERFORM public.fn_create_monthly_partition('tp_trade',  'fills',                v_year, v_month);
        PERFORM public.fn_create_monthly_partition('tp_notify', 'notifications',        v_year, v_month);
        PERFORM public.fn_create_monthly_partition('tp_audit',  'audit_order_history',  v_year, v_month);
    END LOOP;
END;
$$;

-- =====================================================
-- 파티션 분리(아카이빙용) 헬퍼 함수
--   사용 예: SELECT public.fn_detach_old_partition('tp_market','price_minute','2025-01-01');
-- =====================================================
CREATE OR REPLACE FUNCTION public.fn_detach_old_partition(
    p_schema    TEXT,
    p_parent    TEXT,
    p_before    DATE
) RETURNS TABLE(detached_partition TEXT) AS $$
DECLARE
    r RECORD;
    v_sql TEXT;
BEGIN
    FOR r IN
        SELECT inhrelid::regclass AS child_name,
               pg_get_expr(c.relpartbound, c.oid) AS bound_def
          FROM pg_inherits i
          JOIN pg_class c ON c.oid = i.inhrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE i.inhparent = format('%I.%I', p_schema, p_parent)::regclass
           AND n.nspname = p_schema
    LOOP
        -- bound 문자열에서 종료일을 파싱해 p_before 이전이면 detach
        IF r.bound_def ~ format('TO \(''%s', to_char(p_before, 'YYYY-MM-DD')) THEN
            v_sql := format('ALTER TABLE %I.%I DETACH PARTITION %s CONCURRENTLY;',
                            p_schema, p_parent, r.child_name);
            EXECUTE v_sql;
            detached_partition := r.child_name::TEXT;
            RETURN NEXT;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION public.fn_detach_old_partition(TEXT,TEXT,DATE)
    IS '지정일 이전 파티션을 DETACH (아카이빙 절차의 1단계)';
