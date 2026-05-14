-- =====================================================
-- TradePilot - 파티셔닝 점검/보강 마이그레이션
-- 파일: 2026_05_partitioning_review.sql
-- 작성자: DBA
-- 작성일: 2026-05-14
--
-- 목적:
--   1) 누락 파티션 자동 생성 함수 보강(미래 N개월까지 한 번에)
--   2) 오래된 파티션 detach + 아카이브 정책 함수
--   3) 파티션 통계 점검 뷰
--   4) DEFAULT 파티션 모니터링(0행 유지 검증)
--
-- 기존:
--   public.fn_create_monthly_partition(parent_schema, parent, year, month)
--   public.fn_detach_old_partition(schema, parent, before)
-- =====================================================

BEGIN;

-- =====================================================
-- 1. 미래 N개월 파티션 일괄 생성 함수
-- =====================================================

CREATE OR REPLACE FUNCTION public.fn_ensure_future_partitions(
    p_months_ahead INT DEFAULT 3
) RETURNS TABLE(partition_name TEXT, created BOOLEAN) AS $$
DECLARE
    v_targets RECORD;
    v_year   INT;
    v_month  INT;
    v_target DATE;
    v_pname  TEXT;
    v_exists BOOLEAN;
BEGIN
    -- 파티션 대상 테이블 목록(schema, parent, key_column)
    FOR v_targets IN
        SELECT * FROM (VALUES
            ('tp_market', 'price_minute'),
            ('tp_trade',  'orders'),
            ('tp_trade',  'fills'),
            ('tp_notify', 'notifications'),
            ('tp_audit',  'audit_order_history')
        ) AS t(parent_schema, parent_table)
    LOOP
        -- 현재 달부터 +N개월까지 생성 보장
        FOR i IN 0..p_months_ahead LOOP
            v_target := (date_trunc('month', CURRENT_DATE) + (i || ' months')::INTERVAL)::DATE;
            v_year   := EXTRACT(YEAR  FROM v_target)::INT;
            v_month  := EXTRACT(MONTH FROM v_target)::INT;
            v_pname  := format('%s_y%sm%s',
                               v_targets.parent_table,
                               v_year,
                               lpad(v_month::TEXT, 2, '0'));

            SELECT EXISTS (
                SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = v_targets.parent_schema
                  AND c.relname = v_pname
            ) INTO v_exists;

            IF NOT v_exists THEN
                PERFORM public.fn_create_monthly_partition(
                    v_targets.parent_schema,
                    v_targets.parent_table,
                    v_year,
                    v_month
                );
                partition_name := v_targets.parent_schema || '.' || v_pname;
                created := TRUE;
            ELSE
                partition_name := v_targets.parent_schema || '.' || v_pname;
                created := FALSE;
            END IF;
            RETURN NEXT;
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION public.fn_ensure_future_partitions(INT)
    IS '대상 파티션 부모(price_minute/orders/fills/notifications/audit_order_history)에 대해
        현재 달부터 N개월 후까지의 파티션을 멱등하게 생성. cron으로 매주 실행 권장.';


-- =====================================================
-- 2. 오래된 파티션 아카이브 처리 함수
--    절차: DETACH → 백업(아카이브) → DROP
--    DETACH 만 본 함수에서 수행. 백업/DROP 은 운영자 스크립트로 분리.
-- =====================================================

CREATE OR REPLACE FUNCTION public.fn_archive_old_partitions(
    p_schema TEXT,
    p_parent TEXT,
    p_retention_months INT
) RETURNS TABLE(detached_partition TEXT, partition_range TEXT) AS $$
DECLARE
    r RECORD;
    v_cutoff DATE;
    v_sql    TEXT;
    v_bound  TEXT;
BEGIN
    v_cutoff := (date_trunc('month', CURRENT_DATE) - (p_retention_months || ' months')::INTERVAL)::DATE;

    FOR r IN
        SELECT c.oid                       AS child_oid,
               n.nspname                   AS child_schema,
               c.relname                   AS child_name,
               pg_get_expr(c.relpartbound, c.oid) AS bound_def
          FROM pg_inherits i
          JOIN pg_class c       ON c.oid = i.inhrelid
          JOIN pg_namespace n   ON n.oid = c.relnamespace
         WHERE i.inhparent = format('%I.%I', p_schema, p_parent)::regclass
           AND n.nspname   = p_schema
    LOOP
        v_bound := r.bound_def;
        -- bound_def 예: FOR VALUES FROM ('2025-01-01 00:00:00+00') TO ('2025-02-01 00:00:00+00')
        -- 종료일이 cutoff 이전이면 detach
        IF v_bound ~ format('TO \(''%s', to_char(v_cutoff, 'YYYY-MM-DD')) THEN
            v_sql := format('ALTER TABLE %I.%I DETACH PARTITION %I.%I CONCURRENTLY;',
                            p_schema, p_parent, r.child_schema, r.child_name);
            BEGIN
                EXECUTE v_sql;
            EXCEPTION WHEN OTHERS THEN
                -- CONCURRENTLY 가 실패하면(예: DEFAULT 파티션 존재 시) 일반 detach
                EXECUTE format('ALTER TABLE %I.%I DETACH PARTITION %I.%I;',
                               p_schema, p_parent, r.child_schema, r.child_name);
            END;
            detached_partition := r.child_schema || '.' || r.child_name;
            partition_range    := v_bound;
            RETURN NEXT;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION public.fn_archive_old_partitions(TEXT,TEXT,INT)
    IS '보관기간 초과 파티션을 DETACH (CONCURRENTLY 시도, 실패 시 일반 detach).
        DETACH 후 백업/DROP 은 별도 운영자 스크립트로 수행.';


-- =====================================================
-- 3. 파티션 통계 뷰
-- =====================================================

CREATE OR REPLACE VIEW tp_audit.v_partition_stats AS
SELECT
    parent_ns.nspname  AS parent_schema,
    parent_c.relname   AS parent_table,
    child_ns.nspname   AS child_schema,
    child_c.relname    AS child_table,
    pg_get_expr(child_c.relpartbound, child_c.oid) AS partition_bound,
    pg_size_pretty(pg_total_relation_size(child_c.oid)) AS total_size,
    pg_size_pretty(pg_relation_size(child_c.oid))       AS table_size,
    s.n_live_tup,
    s.n_dead_tup,
    s.last_vacuum,
    s.last_autovacuum,
    s.last_analyze,
    s.last_autoanalyze
FROM pg_inherits i
JOIN pg_class parent_c       ON parent_c.oid = i.inhparent
JOIN pg_namespace parent_ns  ON parent_ns.oid = parent_c.relnamespace
JOIN pg_class child_c        ON child_c.oid = i.inhrelid
JOIN pg_namespace child_ns   ON child_ns.oid = child_c.relnamespace
LEFT JOIN pg_stat_user_tables s
       ON s.schemaname = child_ns.nspname
      AND s.relname    = child_c.relname
WHERE parent_ns.nspname LIKE 'tp_%'
  AND child_c.relkind  IN ('r','p')
ORDER BY parent_ns.nspname, parent_c.relname, child_c.relname;
COMMENT ON VIEW tp_audit.v_partition_stats IS
    '파티션별 사이즈/통계 뷰. 누락 파티션/DEFAULT 비대화 감지에 활용';


-- =====================================================
-- 4. DEFAULT 파티션 비대화 감시
--    DEFAULT 파티션에 데이터가 누적된다는 것은 = 정규 파티션 미존재 (운영 버그)
-- =====================================================

CREATE OR REPLACE VIEW tp_audit.v_default_partition_health AS
SELECT
    n.nspname        AS schema_name,
    c.relname        AS partition_name,
    s.n_live_tup,
    CASE
        WHEN s.n_live_tup > 0 THEN 'ALERT'
        ELSE 'OK'
    END AS health_status,
    s.last_autoanalyze
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_stat_user_tables s
       ON s.schemaname = n.nspname
      AND s.relname    = c.relname
WHERE c.relname LIKE '%_default'
  AND n.nspname LIKE 'tp_%'
  AND c.relkind = 'r';
COMMENT ON VIEW tp_audit.v_default_partition_health IS
    'DEFAULT 파티션 비대화 감시. n_live_tup>0 이면 정규 파티션 미존재 의심';


-- =====================================================
-- 5. 누락 파티션 감지 뷰 (당월/익월 필수)
-- =====================================================

CREATE OR REPLACE VIEW tp_audit.v_missing_partitions AS
WITH expected AS (
    SELECT
        parent_schema,
        parent_table,
        to_char(d::date, 'YYYY') || 'm' || to_char(d::date, 'MM') AS suffix,
        to_char(d::date, 'YYYY-MM') AS ym
    FROM (VALUES
        ('tp_market', 'price_minute'),
        ('tp_trade',  'orders'),
        ('tp_trade',  'fills'),
        ('tp_notify', 'notifications'),
        ('tp_audit',  'audit_order_history')
    ) AS t(parent_schema, parent_table)
    CROSS JOIN generate_series(
        date_trunc('month', CURRENT_DATE),
        date_trunc('month', CURRENT_DATE) + INTERVAL '2 months',
        INTERVAL '1 month'
    ) AS d
)
SELECT
    e.parent_schema,
    e.parent_table,
    e.ym,
    e.parent_table || '_y' || e.suffix AS expected_partition,
    EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = e.parent_schema
          AND c.relname = e.parent_table || '_y' || e.suffix
    ) AS exists
FROM expected e
ORDER BY e.parent_schema, e.parent_table, e.ym;
COMMENT ON VIEW tp_audit.v_missing_partitions IS
    '당월/익월/익월+1 까지의 파티션 존재 여부. exists=false 면 자동 생성 실패 의심';

COMMIT;


-- =====================================================
-- 운영 적용 가이드
-- =====================================================
-- 1) 매주 일요일 02:00 (cron): 미래 3개월 파티션 보장
--    psql -d $DATABASE_URL -c "SELECT * FROM public.fn_ensure_future_partitions(3);"
--
-- 2) 매월 25일 03:00 (cron): 오래된 파티션 detach (보관기간 초과)
--    -- price_minute 1m: 12개월, 5m/15m/30m: 60개월 (※ 인터벌별 분리는 미래 과제)
--    SELECT * FROM public.fn_archive_old_partitions('tp_market','price_minute', 60);
--    SELECT * FROM public.fn_archive_old_partitions('tp_trade', 'orders',       120);
--    SELECT * FROM public.fn_archive_old_partitions('tp_trade', 'fills',        120);
--    SELECT * FROM public.fn_archive_old_partitions('tp_notify','notifications', 6);
--    SELECT * FROM public.fn_archive_old_partitions('tp_audit', 'audit_order_history', 120);
--
-- 3) 일 1회: 누락 파티션/DEFAULT 비대화 점검
--    SELECT * FROM tp_audit.v_missing_partitions WHERE NOT exists;
--    SELECT * FROM tp_audit.v_default_partition_health WHERE health_status='ALERT';
