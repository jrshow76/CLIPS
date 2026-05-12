-- =====================================================
-- TradePilot - 역할(Role) 및 권한(Grant) 설정
-- 파일: 99_grants.sql
-- 역할:
--   app_user      : 백엔드 API 서버용. 일반 DML(SELECT/INSERT/UPDATE/DELETE)
--   app_worker    : 시세 수집/지표 산출/시그널 워커 (마스터데이터 + 시세 RW)
--   app_readonly  : 리포트/모니터링용. SELECT only
--   app_admin     : 스키마 변경/마이그레이션용
-- =====================================================

-- =====================================================
-- 1. 역할 생성 (이미 존재 시 무시)
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_admin') THEN
        CREATE ROLE app_admin    LOGIN PASSWORD 'CHANGE_ME_admin'    NOSUPERUSER CREATEDB CREATEROLE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user     LOGIN PASSWORD 'CHANGE_ME_user'     NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_worker') THEN
        CREATE ROLE app_worker   LOGIN PASSWORD 'CHANGE_ME_worker'   NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_readonly') THEN
        CREATE ROLE app_readonly LOGIN PASSWORD 'CHANGE_ME_readonly' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END;
$$;

-- ⚠ 운영 환경에서는 위 비밀번호를 즉시 변경한다.
-- ALTER ROLE app_user WITH PASSWORD '<secret>';

-- =====================================================
-- 2. 스키마 USAGE 권한
-- =====================================================
GRANT USAGE ON SCHEMA tp_user, tp_market, tp_analysis, tp_trade, tp_notify, tp_audit TO app_user, app_worker, app_readonly, app_admin;
GRANT USAGE ON SCHEMA public TO app_user, app_worker, app_readonly, app_admin;

-- =====================================================
-- 3. app_admin : DDL/소유권
-- =====================================================
GRANT ALL ON ALL TABLES    IN SCHEMA tp_user, tp_market, tp_analysis, tp_trade, tp_notify, tp_audit TO app_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA tp_user, tp_market, tp_analysis, tp_trade, tp_notify, tp_audit TO app_admin;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA tp_user, tp_market, tp_analysis, tp_trade, tp_notify, tp_audit TO app_admin;

ALTER DEFAULT PRIVILEGES IN SCHEMA tp_user, tp_market, tp_analysis, tp_trade, tp_notify, tp_audit
    GRANT ALL ON TABLES    TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA tp_user, tp_market, tp_analysis, tp_trade, tp_notify, tp_audit
    GRANT ALL ON SEQUENCES TO app_admin;

-- =====================================================
-- 4. app_user : 일반 DML
--   - 감사(tp_audit)는 INSERT만 허용 (append-only)
-- =====================================================

-- tp_user, tp_trade, tp_notify, tp_analysis : 일반 DML
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA tp_user, tp_trade, tp_notify, tp_analysis TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES                IN SCHEMA tp_user, tp_trade, tp_notify, tp_analysis TO app_user;

-- tp_market : 사용자는 SELECT만(마스터/시세는 워커가 갱신)
GRANT SELECT ON ALL TABLES IN SCHEMA tp_market TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA tp_market TO app_user;

-- tp_audit : INSERT만
GRANT INSERT ON ALL TABLES IN SCHEMA tp_audit TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA tp_audit TO app_user;
-- (조회는 별도 admin/리포트 권한만 가능)

ALTER DEFAULT PRIVILEGES IN SCHEMA tp_user, tp_trade, tp_notify, tp_analysis
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA tp_market
    GRANT SELECT ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA tp_audit
    GRANT INSERT ON TABLES TO app_user;

-- =====================================================
-- 5. app_worker : 시세/지표/시그널 적재 권한
-- =====================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA tp_market, tp_analysis TO app_worker;
GRANT USAGE, SELECT ON ALL SEQUENCES                IN SCHEMA tp_market, tp_analysis TO app_worker;

-- 사용자/매매 정보는 SELECT만 (시그널 생성 시 한도/포지션 참조)
GRANT SELECT ON ALL TABLES IN SCHEMA tp_user, tp_trade TO app_worker;
GRANT INSERT ON tp_analysis.signals TO app_worker;
GRANT INSERT ON ALL TABLES IN SCHEMA tp_audit TO app_worker;

ALTER DEFAULT PRIVILEGES IN SCHEMA tp_market, tp_analysis
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_worker;

-- =====================================================
-- 6. app_readonly : 리포트/모니터링
-- =====================================================
GRANT SELECT ON ALL TABLES IN SCHEMA tp_user, tp_market, tp_analysis, tp_trade, tp_notify, tp_audit TO app_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA tp_user, tp_market, tp_analysis, tp_trade, tp_notify, tp_audit
    GRANT SELECT ON TABLES TO app_readonly;

-- pg_stat_statements 조회 권한 (슬로우 쿼리 분석)
GRANT pg_read_all_stats TO app_readonly, app_admin;

-- =====================================================
-- 7. 민감 컬럼 컬럼 단위 권한 (선택 적용)
--   - app_user는 password_hash를 직접 SELECT하지 않도록 제한
--   - 백엔드는 별도 함수/뷰를 통해 인증 수행
-- =====================================================
REVOKE SELECT (password_hash) ON tp_user.users FROM app_readonly;

-- =====================================================
-- 8. 함수 실행 권한
-- =====================================================
GRANT EXECUTE ON FUNCTION public.fn_set_updated_at()                            TO app_user, app_worker;
GRANT EXECUTE ON FUNCTION public.fn_create_monthly_partition(TEXT,TEXT,INT,INT) TO app_admin;
GRANT EXECUTE ON FUNCTION public.fn_detach_old_partition(TEXT,TEXT,DATE)        TO app_admin;

-- =====================================================
-- 9. 권한 검증 쿼리(주석)
-- =====================================================
-- SELECT grantee, table_schema, table_name, privilege_type
--   FROM information_schema.role_table_grants
--  WHERE grantee IN ('app_user','app_worker','app_readonly','app_admin')
--  ORDER BY grantee, table_schema, table_name;
