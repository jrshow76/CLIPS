-- =====================================================
-- TradePilot - Autovacuum / Statistics 튜닝
-- 파일: 2026_05_autovacuum_tuning.sql
-- 작성자: DBA
-- 작성일: 2026-05-14
--
-- 목적:
--   테이블 변경 패턴(고빈도 INSERT / 빈번 UPDATE / append-only)에 따라
--   Autovacuum 임계값을 조정하여 부풀림(bloat) 누적과
--   plan stability 저하를 예방한다.
--
-- 적용 원칙:
--   - 운영 DB 적용은 DBA 확인 후. PoC/개발 DB에서는 부담 적음.
--   - PostgreSQL 13+ 의 `autovacuum_vacuum_insert_*` 옵션 활용.
--   - 시세/감사 테이블(INSERT-only)은 INSERT-based vacuum 임계값을 낮춰
--     인덱스 visibility map 갱신을 자주 유도(Index-Only Scan 효율).
--
-- 모니터링:
--   SELECT * FROM tp_audit.v_table_bloat_estimate;
--   SELECT * FROM pg_stat_user_tables WHERE n_dead_tup > 10000;
-- =====================================================

BEGIN;

-- =====================================================
-- A. 고빈도 UPDATE 테이블 (주문/체결/포지션)
--    Autovacuum 임계값을 낮춰 dead tuple 누적 차단
-- =====================================================

-- orders: 상태 전이(NEW→PARTIAL→FILLED) 빈번
ALTER TABLE tp_trade.orders SET (
    autovacuum_vacuum_scale_factor  = 0.02,
    autovacuum_analyze_scale_factor = 0.02,
    autovacuum_vacuum_threshold     = 1000,
    autovacuum_analyze_threshold    = 1000
);
COMMENT ON TABLE tp_trade.orders IS
    '주문 (월별 RANGE 파티셔닝, 10년 보관). autovacuum scale_factor=0.02 (고빈도 UPDATE)';

-- positions: 체결마다 qty/avg_price/realized_pnl 갱신
ALTER TABLE tp_trade.positions SET (
    autovacuum_vacuum_scale_factor  = 0.05,
    autovacuum_analyze_scale_factor = 0.05
);

-- portfolios: 일별 스냅샷 + 평가금액 잦은 갱신
ALTER TABLE tp_trade.portfolios SET (
    autovacuum_vacuum_scale_factor  = 0.05,
    autovacuum_analyze_scale_factor = 0.05
);

-- daily_pnl: UPSERT 패턴(일내 여러 번)
ALTER TABLE tp_trade.daily_pnl SET (
    autovacuum_vacuum_scale_factor  = 0.05,
    autovacuum_analyze_scale_factor = 0.05
);

-- signals: status 전이(ACTIVE→EXECUTED/IGNORED/EXPIRED) 빈번
ALTER TABLE tp_analysis.signals SET (
    autovacuum_vacuum_scale_factor  = 0.05,
    autovacuum_analyze_scale_factor = 0.05
);

-- notifications: read 플래그 빈번 갱신
ALTER TABLE tp_notify.notifications SET (
    autovacuum_vacuum_scale_factor  = 0.05,
    autovacuum_analyze_scale_factor = 0.05
);

-- =====================================================
-- B. INSERT-only / 대량 적재 테이블
--    INSERT-based vacuum 임계값 조정(PG13+)
-- =====================================================

-- fills: INSERT-only (체결은 수정 없음)
ALTER TABLE tp_trade.fills SET (
    autovacuum_vacuum_insert_scale_factor = 0.05,  -- 5% 적재 시 vacuum (visibility map 갱신)
    autovacuum_analyze_scale_factor       = 0.05
);

-- price_daily: 일배치 INSERT
ALTER TABLE tp_market.price_daily SET (
    autovacuum_vacuum_insert_scale_factor = 0.10,
    autovacuum_analyze_scale_factor       = 0.05
);

-- price_minute: 분 단위 INSERT 대량
ALTER TABLE tp_market.price_minute SET (
    autovacuum_vacuum_insert_scale_factor = 0.05,
    autovacuum_analyze_scale_factor       = 0.05
);

-- indicators_daily: 일배치 INSERT 후 일부 갱신
ALTER TABLE tp_analysis.indicators_daily SET (
    autovacuum_vacuum_insert_scale_factor = 0.10,
    autovacuum_analyze_scale_factor       = 0.05
);

-- recommendations: 일배치 INSERT
ALTER TABLE tp_analysis.recommendations SET (
    autovacuum_vacuum_insert_scale_factor = 0.10,
    autovacuum_analyze_scale_factor       = 0.05
);

-- =====================================================
-- C. 감사 로그 (append-only, 매우 큰 테이블)
--    autovacuum이 너무 자주 도는 것을 방지하면서 통계는 정기 갱신
-- =====================================================

ALTER TABLE tp_user.audit_login SET (
    autovacuum_vacuum_insert_scale_factor = 0.20,
    autovacuum_analyze_scale_factor       = 0.10
);

ALTER TABLE tp_audit.audit_order_history SET (
    autovacuum_vacuum_insert_scale_factor = 0.20,
    autovacuum_analyze_scale_factor       = 0.10
);

ALTER TABLE tp_audit.audit_risk_event SET (
    autovacuum_vacuum_insert_scale_factor = 0.20,
    autovacuum_analyze_scale_factor       = 0.10
);

ALTER TABLE tp_audit.audit_trade_mode SET (
    autovacuum_vacuum_insert_scale_factor = 0.20,
    autovacuum_analyze_scale_factor       = 0.10
);

ALTER TABLE tp_audit.audit_role_change SET (
    autovacuum_vacuum_insert_scale_factor = 0.20,
    autovacuum_analyze_scale_factor       = 0.10
);

-- =====================================================
-- D. 통계 정확도(STATISTICS) 추가 강화
--    32_INDEX_STRATEGY 에서 일부 컬럼만 적용 → 누락 컬럼 보완
-- =====================================================

-- 시그널: user_id, status 분포 비대칭 → 통계 강화
ALTER TABLE tp_analysis.signals
    ALTER COLUMN user_id      SET STATISTICS 500,
    ALTER COLUMN status       SET STATISTICS 200,
    ALTER COLUMN generated_at SET STATISTICS 500;

-- 주문: user_id, status, trade_mode
ALTER TABLE tp_trade.orders
    ALTER COLUMN user_id    SET STATISTICS 500,
    ALTER COLUMN status     SET STATISTICS 200,
    ALTER COLUMN trade_mode SET STATISTICS 50;

-- 체결: user_id, stock_id 통계 강화
ALTER TABLE tp_trade.fills
    ALTER COLUMN user_id  SET STATISTICS 500,
    ALTER COLUMN stock_id SET STATISTICS 500;

-- 알림: user_id (파티션마다 통계 적용됨)
ALTER TABLE tp_notify.notifications
    ALTER COLUMN user_id    SET STATISTICS 500,
    ALTER COLUMN event_type SET STATISTICS 200;

-- =====================================================
-- E. fill factor 조정 (HOT update 활성화)
--    UPDATE 빈번 테이블에 fillfactor를 낮춰 HOT update 가능성↑
-- =====================================================

-- orders: 상태 전이 시 같은 페이지 내 HOT update 가능성 활용
ALTER TABLE tp_trade.orders SET (fillfactor = 90);

-- positions: 자주 갱신
ALTER TABLE tp_trade.positions SET (fillfactor = 80);

-- daily_pnl: 일중 여러 번 갱신
ALTER TABLE tp_trade.daily_pnl SET (fillfactor = 85);

-- signals: status 전이
ALTER TABLE tp_analysis.signals SET (fillfactor = 85);

-- notifications: read 플래그 갱신 (파티션 부모 - 자식 자동 적용)
ALTER TABLE tp_notify.notifications SET (fillfactor = 85);

COMMIT;

-- =====================================================
-- 적용 후 확인 SQL
-- =====================================================
-- 1) 테이블별 reloptions 확인
--    SELECT n.nspname || '.' || c.relname AS table_name, c.reloptions
--      FROM pg_class c
--      JOIN pg_namespace n ON n.oid = c.relnamespace
--     WHERE c.reloptions IS NOT NULL
--       AND n.nspname LIKE 'tp_%'
--     ORDER BY 1;
--
-- 2) ANALYZE 수동 실행 권장(통계 즉시 갱신)
--    ANALYZE tp_trade.orders;
--    ANALYZE tp_trade.fills;
--    ANALYZE tp_trade.positions;
--    ANALYZE tp_trade.portfolios;
--    ANALYZE tp_analysis.signals;
--    ANALYZE tp_market.price_daily;
--    ANALYZE tp_market.price_minute;
--    ANALYZE tp_notify.notifications;
--
-- 3) Bloat 모니터링
--    SELECT * FROM tp_audit.v_table_bloat_estimate
--     WHERE dead_pct > 10
--     ORDER BY dead_pct DESC;
--
-- 4) Autovacuum 진행 상황
--    SELECT pid, datname, relid::regclass, phase, heap_blks_total, heap_blks_scanned
--      FROM pg_stat_progress_vacuum;
