-- =====================================================
-- TradePilot - 성능 인덱스 추가 마이그레이션
-- 파일: 2026_05_add_performance_indexes.sql
-- 작성자: DBA
-- 작성일: 2026-05-14
--
-- 본 마이그레이션은 90_query_catalog.md 의 정성 분석 결과를
-- 기반으로 누락 인덱스를 추가한다.
--
-- 적용 원칙:
--   1) 모든 인덱스는 `IF NOT EXISTS` (멱등성)
--   2) 운영 적용 시 `CREATE INDEX CONCURRENTLY` 사용 (트랜잭션 외부)
--      - 본 파일은 init 흐름에서 트랜잭션 안에서도 동작하도록
--        CONCURRENTLY 미사용. 운영 적용은 별도 스크립트로 수행.
--   3) 인덱스마다 `COMMENT ON INDEX`로 용도 명시
--   4) 파티션 부모에 선언하여 자식 자동 전파(PG11+)
--
-- 운영 적용 절차(필수):
--   psql -h <host> -d <db> -v ON_ERROR_STOP=1 \
--     -c "SET lock_timeout = '5s';" \
--     -c "SET statement_timeout = 0;"  # 인덱스 빌드는 시간이 걸릴 수 있음
--   각 CREATE INDEX 를 CONCURRENTLY 로 바꾸어 1건씩 실행한다.
--   (CONCURRENTLY 는 트랜잭션 블록 내에서 실행 불가)
-- =====================================================

BEGIN;

-- =====================================================
-- A. 사용자 도메인 (tp_user)
-- =====================================================

-- U-05: revoke_all_for_user 가 자주 호출됨.
--       전체 sessions 중 활성(revoked_at IS NULL)만 빠르게 골라야 함.
CREATE INDEX IF NOT EXISTS idx_sessions_active_user
    ON tp_user.sessions (user_id)
    WHERE revoked_at IS NULL;
COMMENT ON INDEX tp_user.idx_sessions_active_user
    IS '활성 세션 사용자별 조회/일괄 폐기용 partial 인덱스 (U-05)';

-- U-06: 만료 세션 정리 배치 (delete_expired)
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at
    ON tp_user.sessions (expires_at);
COMMENT ON INDEX tp_user.idx_sessions_expires_at
    IS '만료 세션 일괄 삭제(cron) 가속용 (U-06)';

-- 로그인 실패 패턴 모니터링(보안)
CREATE INDEX IF NOT EXISTS idx_audit_login_fail_user
    ON tp_user.audit_login (user_id, created_at DESC)
    WHERE result = 'FAIL';
COMMENT ON INDEX tp_user.idx_audit_login_fail_user
    IS '사용자별 로그인 실패 이력 추적 partial 인덱스(보안 모니터)';

-- =====================================================
-- B. 시장 도메인 (tp_market)
-- =====================================================

-- M-04: 대표 섹터(is_primary=true)만 자주 조회
CREATE INDEX IF NOT EXISTS idx_stock_sectors_primary
    ON tp_market.stock_sectors (stock_id)
    WHERE is_primary = TRUE;
COMMENT ON INDEX tp_market.idx_stock_sectors_primary
    IS '종목 대표 섹터 조회 partial 인덱스 (M-04 get_primary_sector)';

-- =====================================================
-- C. 분석 도메인 (tp_analysis)
-- =====================================================

-- A-11 보조: signals 상태별 빠른 카운트(IGNORED 등 ACTIVE 외 상태)
--           ACTIVE는 idx_signals_active partial 이 이미 처리.
--           IGNORED 카운트가 잦은 화면이 있다면 활성화.
--           ※ 운영 후 사용도 보고 결정. 일단 생성하지 않음(과도한 인덱스 회피).
-- (의도적으로 생성하지 않음)

-- =====================================================
-- D. 매매 도메인 (tp_trade)
-- =====================================================

-- T-06: 주문 이력 화면에서 status 필터가 일상적 (ALL/FILLED/CANCELED 등 탭)
--       기존 (user_id, ordered_at DESC) 만으로는 Filter(status) 비용 발생
CREATE INDEX IF NOT EXISTS idx_orders_user_status_ordered
    ON tp_trade.orders (user_id, status, ordered_at DESC);
COMMENT ON INDEX tp_trade.idx_orders_user_status_ordered
    IS '주문 이력 화면 (user_id, status, ordered_at DESC) 복합 인덱스 (T-06)';

-- T-09: KillSwitch / 미체결 일괄 조회 → 사용자별 미체결만
CREATE INDEX IF NOT EXISTS idx_orders_user_open
    ON tp_trade.orders (user_id, status)
    WHERE status IN ('NEW','PARTIAL','PENDING');
COMMENT ON INDEX tp_trade.idx_orders_user_open
    IS '사용자 미체결 주문 일괄 조회/KillSwitch partial 인덱스 (T-09)';

-- 주문 모드(SIM/LIVE)별 일일 매수 카운트 가속용
-- (count_daily_buys 가 trade_mode를 명시하지 않지만, 향후 SIM/LIVE 분리 시 활용)
CREATE INDEX IF NOT EXISTS idx_orders_user_mode_ordered
    ON tp_trade.orders (user_id, trade_mode, ordered_at DESC);
COMMENT ON INDEX tp_trade.idx_orders_user_mode_ordered
    IS '사용자별 모드(SIM/LIVE) 기간 집계 복합 인덱스 (T-03 변형)';

-- T-13: 보유 포지션 활성 카운트 (qty>0)
CREATE INDEX IF NOT EXISTS idx_positions_user_active
    ON tp_trade.positions (user_id, trade_mode)
    WHERE qty > 0;
COMMENT ON INDEX tp_trade.idx_positions_user_active
    IS '활성 포지션(qty>0) 카운트/리스트 partial 인덱스 (T-13)';

-- T-14: 포트폴리오 최신 스냅샷(모드별)
CREATE INDEX IF NOT EXISTS idx_portfolios_user_mode_snap
    ON tp_trade.portfolios (user_id, trade_mode, snapshot_at DESC);
COMMENT ON INDEX tp_trade.idx_portfolios_user_mode_snap
    IS '포트폴리오 모드별 최신 스냅샷 복합 인덱스 (T-14)';

-- 백테스트 결과 정렬 가속(보조)
CREATE INDEX IF NOT EXISTS idx_bt_results_saved
    ON tp_trade.backtest_results (saved_at DESC);
COMMENT ON INDEX tp_trade.idx_bt_results_saved
    IS '저장된 백테스트 결과 최신순 정렬 보조 인덱스 (T-22)';

-- =====================================================
-- E. 알림 도메인 (tp_notify)
-- =====================================================

-- N-06: 알림 룰 매칭 (active=true 만)
CREATE INDEX IF NOT EXISTS idx_alert_user_event_active
    ON tp_notify.alert_rules (user_id, event_type)
    WHERE active = TRUE;
COMMENT ON INDEX tp_notify.idx_alert_user_event_active
    IS '활성 알림 룰 매칭 partial 인덱스 (N-06)';

-- N-07: 미발송 알림 큐 (Celery worker 폴링)
--   파티션 부모에 선언 → 자식 자동 전파
CREATE INDEX IF NOT EXISTS idx_noti_pending_send
    ON tp_notify.notifications (created_at)
    WHERE sent_at IS NULL;
COMMENT ON INDEX tp_notify.idx_noti_pending_send
    IS '미발송 알림 큐(Celery worker) partial 인덱스 (N-07)';

-- =====================================================
-- F. 감사 도메인 (tp_audit)
-- =====================================================

-- AU-05: 운영자 화면 risk 이벤트 (severity WARN/CRITICAL 만)
CREATE INDEX IF NOT EXISTS idx_are_severity_ts
    ON tp_audit.audit_risk_event (severity, created_at DESC)
    WHERE severity IN ('WARN','CRITICAL');
COMMENT ON INDEX tp_audit.idx_are_severity_ts
    IS '운영자 risk 이벤트 severity 필터 partial 인덱스 (AU-05)';

-- =====================================================
-- G. 인덱스 사용도 모니터링 뷰
-- =====================================================

-- 인덱스 사용도(idx_scan, tup_read 등) 운영자 점검용 래퍼 뷰
CREATE OR REPLACE VIEW tp_audit.v_index_usage AS
SELECT
    s.schemaname,
    s.relname            AS table_name,
    s.indexrelname       AS index_name,
    s.idx_scan,                                    -- 인덱스가 사용된 횟수
    s.idx_tup_read,
    s.idx_tup_fetch,
    pg_size_pretty(pg_relation_size(s.indexrelid))             AS index_size,
    pg_size_pretty(pg_relation_size(s.relid))                  AS table_size,
    CASE
        WHEN s.idx_scan = 0 AND s.indexrelname NOT LIKE 'uq_%'
                          AND s.indexrelname NOT LIKE '%_pkey'
            THEN 'UNUSED'
        WHEN s.idx_scan < 100 THEN 'LOW'
        WHEN s.idx_scan < 10000 THEN 'MEDIUM'
        ELSE 'HIGH'
    END AS usage_band
FROM pg_stat_user_indexes s
WHERE s.schemaname LIKE 'tp_%'
ORDER BY s.idx_scan ASC, pg_relation_size(s.indexrelid) DESC;
COMMENT ON VIEW tp_audit.v_index_usage IS
    '인덱스 사용도 점검 뷰. usage_band=UNUSED 가 3개월 이상 지속되면 제거 검토';

-- 인덱스 중복 후보 뷰
CREATE OR REPLACE VIEW tp_audit.v_index_duplicates AS
SELECT
    pg_get_indexdef(a.indexrelid)::text AS idx_a_def,
    pg_get_indexdef(b.indexrelid)::text AS idx_b_def,
    a.indexrelid::regclass               AS idx_a,
    b.indexrelid::regclass               AS idx_b,
    pg_size_pretty(pg_relation_size(a.indexrelid)) AS size_a,
    pg_size_pretty(pg_relation_size(b.indexrelid)) AS size_b
FROM pg_index a
JOIN pg_index b ON a.indrelid = b.indrelid
JOIN pg_class ca ON ca.oid = a.indexrelid
JOIN pg_class cb ON cb.oid = b.indexrelid
JOIN pg_namespace na ON na.oid = ca.relnamespace
WHERE a.indexrelid < b.indexrelid
  AND a.indkey::text = b.indkey::text
  AND na.nspname LIKE 'tp_%';
COMMENT ON VIEW tp_audit.v_index_duplicates IS
    '동일한 컬럼 집합을 가지는 중복 인덱스 후보 뷰';

-- 테이블 부풀림(bloat) 추정 뷰 (pgstattuple 확장 미사용 간단 추정)
CREATE OR REPLACE VIEW tp_audit.v_table_bloat_estimate AS
SELECT
    n.nspname || '.' || c.relname AS table_name,
    pg_size_pretty(pg_total_relation_size(c.oid))     AS total_size,
    pg_size_pretty(pg_relation_size(c.oid))           AS table_size,
    s.n_live_tup,
    s.n_dead_tup,
    CASE
        WHEN s.n_live_tup > 0
            THEN ROUND(100.0 * s.n_dead_tup / s.n_live_tup, 2)
        ELSE 0
    END AS dead_pct,
    s.last_vacuum,
    s.last_autovacuum
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_stat_user_tables s
    ON s.schemaname = n.nspname AND s.relname = c.relname
WHERE n.nspname LIKE 'tp_%'
  AND c.relkind = 'r'
ORDER BY (CASE WHEN s.n_live_tup > 0 THEN s.n_dead_tup::numeric / s.n_live_tup ELSE 0 END) DESC;
COMMENT ON VIEW tp_audit.v_table_bloat_estimate IS
    '테이블 데드튜플 비율(부풀림) 추정 뷰. dead_pct > 20%면 VACUUM 검토';

COMMIT;

-- =====================================================
-- 운영자 점검 SQL (마이그레이션 이후)
-- =====================================================
-- 1. 인덱스가 실제 사용되고 있는가?
--    SELECT * FROM tp_audit.v_index_usage WHERE usage_band='UNUSED';
--
-- 2. 중복 인덱스가 있는가?
--    SELECT * FROM tp_audit.v_index_duplicates;
--
-- 3. 새 인덱스에 대해 ANALYZE 실행 (선택 통계 갱신)
--    ANALYZE tp_trade.orders;
--    ANALYZE tp_trade.positions;
--    ANALYZE tp_trade.portfolios;
--    ANALYZE tp_user.sessions;
--    ANALYZE tp_notify.notifications;
--    ANALYZE tp_audit.audit_risk_event;
