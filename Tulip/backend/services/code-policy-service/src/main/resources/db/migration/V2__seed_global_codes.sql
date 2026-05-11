-- =====================================================================
-- Tulip+ code-policy-service — V2 글로벌 코드 시드 (Sprint 1-C)
-- ---------------------------------------------------------------------
-- 작성자 : DBA Agent
-- 작성일 : 2026-05-11
-- 변경요약: 글로벌 코드 그룹 5종 + 그룹별 표준 코드 시드
--           - MEMBER_TYPE  (일반/학생/교사/직원/단체)
--           - LIBRARY_TYPE (중앙/분관/통합)
--           - ITEM_TYPE    (도서/연속간행물/비도서/디지털)
--           - LOAN_STATUS  (가능/대출중/예약중/연체/분실)
--           - CONSENT_KIND (마케팅/개인정보/3자제공)
-- 정책   : tenant_id IS NULL (글로벌). 모든 테넌트 공유.
--          RLS 에 의해 SELECT 는 전 사용자, 변경은 SYS_ADMIN 만.
--          본 시드는 마이그레이션 트랜잭션이 BYPASSRLS 권한으로 실행됨을 전제.
-- =====================================================================

-- 코드 그룹 시드
INSERT INTO cd_code_group (tenant_id, group_code, name, description, system_yn)
VALUES
    (NULL, 'MEMBER_TYPE',  '회원 유형',      '도서관 회원 분류 (일반/학생/교사/직원/단체)', TRUE),
    (NULL, 'LIBRARY_TYPE', '도서관 유형',    '도서관 형태 (중앙/분관/통합)',                TRUE),
    (NULL, 'ITEM_TYPE',    '자료 유형',      '자료 분류 (도서/연속간행물/비도서/디지털)',    TRUE),
    (NULL, 'LOAN_STATUS',  '대출 상태',      '대출 트랜잭션 상태값',                       TRUE),
    (NULL, 'CONSENT_KIND', '동의 종류',      '회원 동의 종류 (마케팅/개인정보/3자제공)',     TRUE)
ON CONFLICT DO NOTHING;

-- =====================================================================
-- MEMBER_TYPE
-- =====================================================================
WITH g AS (
    SELECT id FROM cd_code_group WHERE tenant_id IS NULL AND group_code = 'MEMBER_TYPE'
)
INSERT INTO cd_code (tenant_id, group_id, code, name, sort_order, system_yn, attrs_json)
SELECT NULL, g.id, v.code, v.name, v.sort_order, TRUE, v.attrs_json::jsonb
FROM g,
     (VALUES
        ('GENERAL',  '일반',  10, '{"loan_limit_default":5}'),
        ('STUDENT',  '학생',  20, '{"loan_limit_default":3}'),
        ('TEACHER',  '교사',  30, '{"loan_limit_default":10}'),
        ('STAFF',    '직원',  40, '{"loan_limit_default":10}'),
        ('GROUP',    '단체',  50, '{"loan_limit_default":30}')
     ) AS v(code, name, sort_order, attrs_json)
ON CONFLICT DO NOTHING;

-- =====================================================================
-- LIBRARY_TYPE
-- =====================================================================
WITH g AS (
    SELECT id FROM cd_code_group WHERE tenant_id IS NULL AND group_code = 'LIBRARY_TYPE'
)
INSERT INTO cd_code (tenant_id, group_id, code, name, sort_order, system_yn)
SELECT NULL, g.id, v.code, v.name, v.sort_order, TRUE
FROM g,
     (VALUES
        ('CENTRAL',    '중앙관', 10),
        ('BRANCH',     '분관',   20),
        ('INTEGRATED', '통합',   30)
     ) AS v(code, name, sort_order)
ON CONFLICT DO NOTHING;

-- =====================================================================
-- ITEM_TYPE
-- =====================================================================
WITH g AS (
    SELECT id FROM cd_code_group WHERE tenant_id IS NULL AND group_code = 'ITEM_TYPE'
)
INSERT INTO cd_code (tenant_id, group_id, code, name, sort_order, system_yn, attrs_json)
SELECT NULL, g.id, v.code, v.name, v.sort_order, TRUE, v.attrs_json::jsonb
FROM g,
     (VALUES
        ('BOOK',       '도서',          10, '{"loanable":true,"default_period_days":14}'),
        ('SERIAL',     '연속간행물',     20, '{"loanable":true,"default_period_days":7}'),
        ('NONBOOK',    '비도서',        30, '{"loanable":true,"default_period_days":7}'),
        ('DIGITAL',    '디지털자료',     40, '{"loanable":false}')
     ) AS v(code, name, sort_order, attrs_json)
ON CONFLICT DO NOTHING;

-- =====================================================================
-- LOAN_STATUS
-- =====================================================================
WITH g AS (
    SELECT id FROM cd_code_group WHERE tenant_id IS NULL AND group_code = 'LOAN_STATUS'
)
INSERT INTO cd_code (tenant_id, group_id, code, name, sort_order, system_yn)
SELECT NULL, g.id, v.code, v.name, v.sort_order, TRUE
FROM g,
     (VALUES
        ('AVAILABLE', '가능',   10),
        ('ON_LOAN',   '대출중', 20),
        ('RESERVED',  '예약중', 30),
        ('OVERDUE',   '연체',   40),
        ('LOST',      '분실',   50)
     ) AS v(code, name, sort_order)
ON CONFLICT DO NOTHING;

-- =====================================================================
-- CONSENT_KIND
-- =====================================================================
WITH g AS (
    SELECT id FROM cd_code_group WHERE tenant_id IS NULL AND group_code = 'CONSENT_KIND'
)
INSERT INTO cd_code (tenant_id, group_id, code, name, sort_order, system_yn, attrs_json)
SELECT NULL, g.id, v.code, v.name, v.sort_order, TRUE, v.attrs_json::jsonb
FROM g,
     (VALUES
        ('MARKETING',   '마케팅 수신 동의',     10, '{"required":false}'),
        ('PRIVACY',     '개인정보 수집/이용',   20, '{"required":true}'),
        ('THIRD_PARTY', '제3자 제공 동의',      30, '{"required":false}')
     ) AS v(code, name, sort_order, attrs_json)
ON CONFLICT DO NOTHING;

-- 끝.
