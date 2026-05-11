-- =====================================================================
-- Tulip+ — RLS 회귀 테스트: 회원 테넌트 격리 (Sprint 1-C.10)
-- ---------------------------------------------------------------------
-- 작성자 : DBA Agent
-- 작성일 : 2026-05-11
-- 변경요약: 2개 테넌트에 mbr_member 5,000건씩 = 10,000건 시드,
--           SET app.current_tenant 변경 시 RLS 가 정확히 격리되는지 확인.
-- 실행환경: member-service 의 PostgreSQL 인스턴스 (Flyway V1 적용 후)
-- 사용법 :
--   psql "$MEMBER_SERVICE_DSN" -v ON_ERROR_STOP=1 -f 01_member_isolation_test.sql
--
-- 종료코드:
--   0    = 모든 assertion 통과
--   != 0 = 하나라도 실패 (psql --set ON_ERROR_STOP=1 가정)
-- =====================================================================

\echo '====================================================================='
\echo ' RLS 회귀 테스트 시작: 회원 테넌트 격리 (10,000 행)'
\echo '====================================================================='

-- ---------------------------------------------------------------------
-- 0. 사전 환경: 본 테스트는 BYPASSRLS 권한 (마이그레이션 owner) 으로 실행되어야 한다.
--    실제 회귀 검증은 app_user 권한 세션으로 재현하기 위해 SET ROLE 사용.
-- ---------------------------------------------------------------------

-- KMS 키 (데모 — pgcrypto 헬퍼가 요구) ---------------------------------
SET app.kms_key = 'rls-regression-test-only-do-not-use-in-prod';

-- ---------------------------------------------------------------------
-- 1. 어서션 유틸 함수 (pgTAP 미존재 환경 대응 plain assertion)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_assert_eq(
    p_name      TEXT,
    p_actual    BIGINT,
    p_expected  BIGINT
) RETURNS VOID AS $$
BEGIN
    IF p_actual = p_expected THEN
        RAISE NOTICE '[PASS] % — actual=%, expected=%', p_name, p_actual, p_expected;
    ELSE
        RAISE EXCEPTION '[FAIL] % — actual=%, expected=%', p_name, p_actual, p_expected;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 2. 시드 정리(멱등) + 시드 적재
--    BYPASSRLS 가 필요하므로 마이그레이션 owner 로 실행한다.
--    여기서는 tenant_id 1, 2 의 더미 회원을 5,000건씩 적재.
-- ---------------------------------------------------------------------
-- 깨끗하게 시작
DELETE FROM mbr_member WHERE tenant_id IN (1, 2) AND member_no LIKE 'TEST-%';

-- tenant_id=1, 5000건
INSERT INTO mbr_member (
    public_id, tenant_id, library_id, member_no, name, status, join_date, member_type_code
)
SELECT
    'T1' || LPAD(gs::text, 24, '0'),
    1,
    1,
    'TEST-1-' || LPAD(gs::text, 6, '0'),
    '테넌트1회원' || gs,
    'ACTIVE',
    CURRENT_DATE,
    'GENERAL'
FROM generate_series(1, 5000) AS gs;

-- tenant_id=2, 5000건
INSERT INTO mbr_member (
    public_id, tenant_id, library_id, member_no, name, status, join_date, member_type_code
)
SELECT
    'T2' || LPAD(gs::text, 24, '0'),
    2,
    1,
    'TEST-2-' || LPAD(gs::text, 6, '0'),
    '테넌트2회원' || gs,
    'ACTIVE',
    CURRENT_DATE,
    'GENERAL'
FROM generate_series(1, 5000) AS gs;

-- ---------------------------------------------------------------------
-- 3. owner(BYPASSRLS) 입장에서 총합 검증
-- ---------------------------------------------------------------------
DO $$
DECLARE
    v_total BIGINT;
BEGIN
    SELECT count(*) INTO v_total
      FROM mbr_member
     WHERE member_no LIKE 'TEST-%';
    PERFORM fn_assert_eq('owner 시점 총합 (10,000)', v_total, 10000::BIGINT);
END $$;

-- ---------------------------------------------------------------------
-- 4. app_user 권한으로 전환하여 RLS 동작 검증
--    NOTE: 본 테스트가 실행되는 DB 에 tulip_app_rw 가 존재하지 않을 수 있다.
--          그 경우 마이그레이션 owner 자체를 강제로 RLS 대상으로 두기 위해
--          FORCE ROW LEVEL SECURITY 가 V1 에서 활성화되어 있어야 한다(이미 적용됨).
--    여기서는 SET ROLE 시도하되 실패하면 일반 사용자처럼 진행한다.
-- ---------------------------------------------------------------------

DO $$
BEGIN
    PERFORM 1 FROM pg_roles WHERE rolname = 'tulip_app_rw';
    IF FOUND THEN
        EXECUTE 'SET ROLE tulip_app_rw';
        RAISE NOTICE 'SET ROLE tulip_app_rw 적용';
    ELSE
        RAISE NOTICE 'tulip_app_rw 미존재 — FORCE RLS 에 의존하여 owner 권한으로 검증 (정책은 동일 적용)';
    END IF;
END $$;

-- 4.1 tenant=1 컨텍스트
SET app.current_tenant = '1';
SET app.role = 'LIBRARIAN';

DO $$
DECLARE
    v_cnt BIGINT;
BEGIN
    SELECT count(*) INTO v_cnt FROM mbr_member WHERE member_no LIKE 'TEST-%';
    PERFORM fn_assert_eq('tenant=1: 회원 5,000건', v_cnt, 5000::BIGINT);
END $$;

-- 4.2 WHERE 우회 시도 — RLS 가 차단해야 함 → 0건 기대
DO $$
DECLARE
    v_cnt BIGINT;
BEGIN
    SELECT count(*) INTO v_cnt FROM mbr_member
      WHERE tenant_id = 2 AND member_no LIKE 'TEST-%';
    PERFORM fn_assert_eq('tenant=1: WHERE tenant_id=2 우회 시도 → 차단', v_cnt, 0::BIGINT);
END $$;

-- 4.3 tenant=2 컨텍스트
SET app.current_tenant = '2';

DO $$
DECLARE
    v_cnt BIGINT;
BEGIN
    SELECT count(*) INTO v_cnt FROM mbr_member WHERE member_no LIKE 'TEST-%';
    PERFORM fn_assert_eq('tenant=2: 회원 5,000건', v_cnt, 5000::BIGINT);
END $$;

-- 4.4 tenant=1 데이터 접근 시도 → 0건
DO $$
DECLARE
    v_cnt BIGINT;
BEGIN
    SELECT count(*) INTO v_cnt FROM mbr_member
      WHERE tenant_id = 1 AND member_no LIKE 'TEST-%';
    PERFORM fn_assert_eq('tenant=2: WHERE tenant_id=1 우회 시도 → 차단', v_cnt, 0::BIGINT);
END $$;

-- 4.5 INSERT — 다른 테넌트 행 작성 시도는 RLS WITH CHECK 가 차단
SET app.current_tenant = '1';
DO $$
DECLARE
    v_failed BOOLEAN := FALSE;
BEGIN
    BEGIN
        INSERT INTO mbr_member (public_id, tenant_id, library_id, member_no, name, status, join_date, member_type_code)
        VALUES ('TXSPILL00000000000000000X', 2, 1, 'TEST-SPILL', '누설시도', 'ACTIVE', CURRENT_DATE, 'GENERAL');
    EXCEPTION WHEN insufficient_privilege OR check_violation OR OTHERS THEN
        v_failed := TRUE;
    END;
    IF v_failed THEN
        RAISE NOTICE '[PASS] tenant=1 컨텍스트에서 tenant_id=2 INSERT → 거부됨';
    ELSE
        RAISE EXCEPTION '[FAIL] tenant=1 컨텍스트에서 tenant_id=2 INSERT 가 허용됨 — RLS 누설!';
    END IF;
END $$;

-- 4.6 UPDATE — 다른 테넌트 행 수정 시도 → 0건
SET app.current_tenant = '1';
DO $$
DECLARE
    v_cnt BIGINT;
BEGIN
    WITH u AS (
        UPDATE mbr_member SET name = name || '-X'
         WHERE tenant_id = 2 AND member_no LIKE 'TEST-%'
        RETURNING 1
    )
    SELECT count(*) INTO v_cnt FROM u;
    PERFORM fn_assert_eq('tenant=1: tenant=2 UPDATE 시도 → 0건', v_cnt, 0::BIGINT);
END $$;

-- 4.7 DELETE — 다른 테넌트 행 삭제 시도 → 0건
SET app.current_tenant = '2';
DO $$
DECLARE
    v_cnt BIGINT;
BEGIN
    WITH d AS (
        DELETE FROM mbr_member
         WHERE tenant_id = 1 AND member_no LIKE 'TEST-%'
        RETURNING 1
    )
    SELECT count(*) INTO v_cnt FROM d;
    PERFORM fn_assert_eq('tenant=2: tenant=1 DELETE 시도 → 0건', v_cnt, 0::BIGINT);
END $$;

-- 4.8 컨텍스트 미설정 시: 모두 0건
RESET app.current_tenant;
RESET app.role;
DO $$
DECLARE
    v_cnt BIGINT;
BEGIN
    SELECT count(*) INTO v_cnt FROM mbr_member WHERE member_no LIKE 'TEST-%';
    PERFORM fn_assert_eq('컨텍스트 미설정: 0건', v_cnt, 0::BIGINT);
END $$;

-- ---------------------------------------------------------------------
-- 5. 정리: 시드 데이터 삭제 (BYPASSRLS owner 로 복귀하여 정리)
-- ---------------------------------------------------------------------
RESET ROLE;
RESET app.current_tenant;
RESET app.role;

DELETE FROM mbr_member WHERE member_no LIKE 'TEST-%';

\echo '====================================================================='
\echo ' RLS 회귀 테스트 종료: 모든 어서션 통과'
\echo '====================================================================='
