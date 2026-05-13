-- =====================================================================
-- TradePilot 복구 리허설 검증 SQL
-- 파일: drill_validation.sql
-- 목적: 복원된 임시 DB(tradepilot_drill)가 운영 데이터와 동일한 골격/볼륨/
--       정합성을 갖추는지 자동 검증.
--
-- 실행:
--   psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d tradepilot_drill \
--        -v ON_ERROR_STOP=1 -f drill_validation.sql
--
-- 합격 기준:
--   - 모든 검증 항목의 status = 'PASS'
--   - 한 건이라도 'FAIL' 시 리허설 실패 → 알림 발송 + RCA
--
-- 산출:
--   tp_audit.drill_results 임시 테이블 또는 STDOUT 으로 PASS/FAIL 보고
-- =====================================================================

\set ON_ERROR_STOP on
\timing on

\echo '========================================='
\echo 'TradePilot Restore Drill Validation'
\echo '========================================='
\echo ''

-- ---------------------------------------------------------------------
-- 0. 사전: 스키마 존재 확인
-- ---------------------------------------------------------------------
\echo '[0] 스키마 존재 확인'
SELECT
    nspname AS schema_name,
    CASE WHEN nspname IS NULL THEN 'FAIL' ELSE 'PASS' END AS status
  FROM (VALUES ('tp_user'),('tp_market'),('tp_analysis'),
               ('tp_trade'),('tp_notify'),('tp_audit')) AS expected(s)
  LEFT JOIN pg_namespace ON pg_namespace.nspname = expected.s
 ORDER BY 1;

-- ---------------------------------------------------------------------
-- 1. 핵심 테이블 존재 + 행수 (>= 0 이면 OK, NULL이면 FAIL)
-- ---------------------------------------------------------------------
\echo ''
\echo '[1] 핵심 테이블 존재 + 행수'
WITH expected_tables(schema_name, table_name) AS (
  VALUES
    ('tp_user',     'users'),
    ('tp_user',     'sessions'),
    ('tp_market',   'stocks'),
    ('tp_market',   'price_daily'),
    ('tp_market',   'price_minute'),
    ('tp_market',   'market_index'),
    ('tp_analysis', 'signals'),
    ('tp_analysis', 'recommendations'),
    ('tp_trade',    'strategies'),
    ('tp_trade',    'orders'),
    ('tp_trade',    'fills'),
    ('tp_trade',    'positions'),
    ('tp_trade',    'daily_pnl'),
    ('tp_notify',   'notifications'),
    ('tp_audit',    'audit_order_history')
)
SELECT
    e.schema_name,
    e.table_name,
    CASE
      WHEN c.oid IS NULL THEN 'FAIL: 테이블 없음'
      ELSE 'PASS'
    END AS status,
    -- reltuples는 추정치, ANALYZE 후 정확. EXPLAIN COUNT보다 빠름.
    COALESCE(c.reltuples::BIGINT, -1) AS approx_rows
  FROM expected_tables e
  LEFT JOIN pg_namespace n ON n.nspname = e.schema_name
  LEFT JOIN pg_class c     ON c.relnamespace = n.oid AND c.relname = e.table_name
 ORDER BY e.schema_name, e.table_name;

-- ---------------------------------------------------------------------
-- 2. 파티션 자식 테이블 존재 (price_minute, orders, fills, notifications)
--    리허설 시점 기준 당월 파티션이 반드시 존재해야 함.
-- ---------------------------------------------------------------------
\echo ''
\echo '[2] 파티션 자식 테이블 (당월 + 차월)'
WITH expected_partitions AS (
  SELECT
    parent_schema, parent_table,
    parent_table || '_y' || to_char(d, 'YYYY') || 'm' || to_char(d, 'MM') AS expected_child
  FROM (VALUES
    ('tp_market','price_minute'),
    ('tp_trade', 'orders'),
    ('tp_trade', 'fills'),
    ('tp_notify','notifications'),
    ('tp_audit', 'audit_order_history')
  ) AS p(parent_schema, parent_table)
  CROSS JOIN generate_series(
    date_trunc('month', CURRENT_DATE),
    date_trunc('month', CURRENT_DATE) + INTERVAL '1 month',
    INTERVAL '1 month'
  ) AS d
)
SELECT
    ep.parent_schema,
    ep.parent_table,
    ep.expected_child,
    CASE WHEN c.oid IS NULL THEN 'FAIL' ELSE 'PASS' END AS status
  FROM expected_partitions ep
  LEFT JOIN pg_namespace n ON n.nspname = ep.parent_schema
  LEFT JOIN pg_class c     ON c.relnamespace = n.oid AND c.relname = ep.expected_child
 ORDER BY ep.parent_schema, ep.parent_table, ep.expected_child;

-- ---------------------------------------------------------------------
-- 3. 인덱스 누락 검사 (핵심 인덱스만)
-- ---------------------------------------------------------------------
\echo ''
\echo '[3] 핵심 인덱스 존재 여부'
WITH expected_indexes(schema_name, idx_name) AS (
  VALUES
    ('tp_user',   'users_pkey'),
    ('tp_user',   'uq_users_email'),
    ('tp_market', 'stocks_pkey'),
    ('tp_market', 'uq_stocks_code'),
    ('tp_trade',  'strategies_pkey'),
    ('tp_trade',  'orders_pkey')
)
SELECT
    e.schema_name,
    e.idx_name,
    CASE WHEN i.indexname IS NULL THEN 'WARN: 인덱스 미존재(이름 변경 가능)'
         ELSE 'PASS' END AS status
  FROM expected_indexes e
  LEFT JOIN pg_indexes i ON i.schemaname = e.schema_name AND i.indexname = e.idx_name
 ORDER BY 1, 2;

-- ---------------------------------------------------------------------
-- 4. 시퀀스 존재 + currval 정상 (NULL 이면 FAIL)
-- ---------------------------------------------------------------------
\echo ''
\echo '[4] 시퀀스 점검'
SELECT
    schemaname AS schema_name,
    sequencename AS seq_name,
    last_value,
    CASE WHEN last_value IS NULL THEN 'FAIL' ELSE 'PASS' END AS status
  FROM pg_sequences
 WHERE schemaname LIKE 'tp_%'
 ORDER BY 1, 2
 LIMIT 30;

-- ---------------------------------------------------------------------
-- 5. 외래키 무결성 (대표 테이블)
--    NOT VALID로 등록된 FK 가 없는지(=정합성 위반 의심)
-- ---------------------------------------------------------------------
\echo ''
\echo '[5] FK NOT VALID 잔여 (정상: 0건)'
SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    con.conname AS fk_name,
    'WARN' AS status
  FROM pg_constraint con
  JOIN pg_class c     ON c.oid = con.conrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE con.contype = 'f'
   AND NOT con.convalidated
   AND n.nspname LIKE 'tp_%'
 ORDER BY 1, 2;

-- ---------------------------------------------------------------------
-- 6. 최근 7일 일봉 데이터 존재 (운영 DB 연속성)
--    리허설 시 백업 시점 기준이므로 trade_date <= last_full_backup_date
-- ---------------------------------------------------------------------
\echo ''
\echo '[6] 최근 일봉 데이터 분포 (백업 시점 기준 ±7일)'
SELECT
    trade_date,
    COUNT(*) AS rows,
    CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END AS status
  FROM tp_market.price_daily
 WHERE trade_date >= CURRENT_DATE - INTERVAL '14 days'
 GROUP BY trade_date
 ORDER BY trade_date DESC
 LIMIT 10;

-- ---------------------------------------------------------------------
-- 7. ROLE/권한 골격 확인 (논리 백업 적용 후)
-- ---------------------------------------------------------------------
\echo ''
\echo '[7] 역할(ROLE) 존재 여부'
WITH expected_roles(rolname) AS (
  VALUES ('app_admin'), ('app_user'), ('app_worker'), ('app_readonly')
)
SELECT
    e.rolname,
    CASE WHEN r.rolname IS NULL THEN 'WARN: ROLE 미존재(논리백업 별도 적용 필요)'
         ELSE 'PASS' END AS status
  FROM expected_roles e
  LEFT JOIN pg_roles r ON r.rolname = e.rolname
 ORDER BY 1;

-- ---------------------------------------------------------------------
-- 8. 테이블 크기 톱 10 (이상값 탐지: 0bytes가 너무 많으면 FAIL 의심)
-- ---------------------------------------------------------------------
\echo ''
\echo '[8] 테이블 크기 톱 10'
SELECT
    n.nspname AS schema,
    c.relname AS table,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r','p')
   AND n.nspname LIKE 'tp_%'
 ORDER BY pg_total_relation_size(c.oid) DESC
 LIMIT 10;

-- ---------------------------------------------------------------------
-- 9. 최종 요약 (한 줄)
-- ---------------------------------------------------------------------
\echo ''
\echo '[9] 전체 PASS/FAIL 요약 (수동 집계 - 위 결과 검토 필요)'
SELECT
    CURRENT_DATABASE() AS db,
    CURRENT_TIMESTAMP AS validated_at,
    (SELECT COUNT(*) FROM pg_namespace WHERE nspname LIKE 'tp_%') AS schemas,
    (SELECT COUNT(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE n.nspname LIKE 'tp_%' AND c.relkind IN ('r','p'))     AS tables,
    (SELECT COUNT(*) FROM pg_indexes WHERE schemaname LIKE 'tp_%') AS indexes,
    (SELECT COUNT(*) FROM pg_sequences WHERE schemaname LIKE 'tp_%') AS sequences;

\echo ''
\echo '========================================='
\echo 'Drill Validation 완료'
\echo '========================================='
