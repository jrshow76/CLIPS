-- =====================================================
-- TradePilot - 마이그레이션 추적 인프라
-- 파일: 0000_schema_migrations.sql
-- 스키마: tp_audit
-- 설명:
--   운영 DB 마이그레이션 적용 이력을 영구 보관하기 위한 추적 테이블.
--   migrate_all.sh / migrate_verify.sh / migrate_rollback.sh 가 본 테이블을
--   기준으로 미적용/적용/롤백 상태를 판단한다.
--
-- 보안 / 권한:
--   - app_admin 만 INSERT/UPDATE 허용 (운영자 위임)
--   - app_user / app_worker 는 SELECT 만 허용
--   - app_readonly 는 SELECT 가능 (감사/리포트 용도)
--
-- idempotent: CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS 사용
-- 적용 시점: 가장 먼저(0000_) 모든 마이그레이션의 선행 조건.
-- =====================================================

SET search_path TO tp_audit, public;

-- =====================================================
-- 1. schema_migrations : 마이그레이션 이력
-- =====================================================
CREATE TABLE IF NOT EXISTS tp_audit.schema_migrations (
    id              BIGSERIAL       PRIMARY KEY,
    name            VARCHAR(200)    NOT NULL,                       -- 파일명 (예: 2026_05_add_export_jobs.sql)
    checksum        VARCHAR(64)     NULL,                           -- SHA256 hex
    applied_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    applied_by      VARCHAR(80)     NULL,                           -- OS user / DB role
    duration_ms     INTEGER         NULL,                           -- 적용 소요 ms
    status          VARCHAR(20)     NOT NULL DEFAULT 'SUCCESS',     -- SUCCESS/FAILED/ROLLED_BACK/SKIPPED
    notes           TEXT            NULL,
    CONSTRAINT uq_schema_migrations_name    UNIQUE (name),
    CONSTRAINT ck_schema_migrations_status  CHECK (status IN ('SUCCESS','FAILED','ROLLED_BACK','SKIPPED'))
);

COMMENT ON TABLE  tp_audit.schema_migrations
    IS '마이그레이션 적용 이력. migrate_all.sh / migrate_rollback.sh 가 갱신.
        운영자(app_admin) 외에는 INSERT/UPDATE 금지. 감사/리포트 목적 SELECT 만 허용';
COMMENT ON COLUMN tp_audit.schema_migrations.name
    IS '마이그레이션 SQL 파일명. database/migrations/*.sql 의 basename';
COMMENT ON COLUMN tp_audit.schema_migrations.checksum
    IS 'SHA256(파일 내용). 적용 시점 체크섬과 현재 파일 체크섬이 다르면 무결성 위반(--force 외 차단)';
COMMENT ON COLUMN tp_audit.schema_migrations.applied_by
    IS 'OS 사용자명($USER) 또는 DB role 명. 추적/감사 용도';
COMMENT ON COLUMN tp_audit.schema_migrations.duration_ms
    IS '적용 소요 시간(ms). 정상 적용에서 1분 이상이면 슬로우 마이그레이션으로 분류';
COMMENT ON COLUMN tp_audit.schema_migrations.status
    IS 'SUCCESS: 정상 적용 / FAILED: 적용 중 실패(롤백 완료) / ROLLED_BACK: 역방향 SQL 실행 / SKIPPED: dry-run 등';
COMMENT ON COLUMN tp_audit.schema_migrations.notes
    IS '운영자 메모. 사후 검증 결과나 장애 대응 메모를 누적 기록 가능';

-- =====================================================
-- 2. 인덱스
-- =====================================================
-- 최근 적용 이력 조회 가속
CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at
    ON tp_audit.schema_migrations (applied_at DESC);

-- 상태별 조회(실패만)
CREATE INDEX IF NOT EXISTS idx_schema_migrations_status
    ON tp_audit.schema_migrations (status)
    WHERE status IN ('FAILED','ROLLED_BACK');

-- =====================================================
-- 3. 권한
-- =====================================================
-- app_admin: 마이그레이션 적용 주체 (INSERT/UPDATE/DELETE)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_admin') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON tp_audit.schema_migrations TO app_admin;
        GRANT USAGE, SELECT ON SEQUENCE tp_audit.schema_migrations_id_seq TO app_admin;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_readonly') THEN
        GRANT SELECT ON tp_audit.schema_migrations TO app_readonly;
    END IF;
    -- app_user / app_worker 는 SELECT 만 허용(감사 정책상 직접 변경 차단)
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_user') THEN
        GRANT SELECT ON tp_audit.schema_migrations TO app_user;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_worker') THEN
        GRANT SELECT ON tp_audit.schema_migrations TO app_worker;
    END IF;
END$$;

-- =====================================================
-- 4. 운영 보조 뷰
-- =====================================================
-- 최근 적용된 N건
CREATE OR REPLACE VIEW tp_audit.v_recent_migrations AS
SELECT id, name, status, applied_at, applied_by, duration_ms, notes
  FROM tp_audit.schema_migrations
 ORDER BY applied_at DESC
 LIMIT 50;
COMMENT ON VIEW tp_audit.v_recent_migrations IS '최근 50건 마이그레이션 이력. 운영자 대시보드 / 장애 후 조사용';

-- 실패/롤백만
CREATE OR REPLACE VIEW tp_audit.v_failed_migrations AS
SELECT id, name, status, applied_at, applied_by, duration_ms, notes
  FROM tp_audit.schema_migrations
 WHERE status IN ('FAILED','ROLLED_BACK')
 ORDER BY applied_at DESC;
COMMENT ON VIEW tp_audit.v_failed_migrations IS '실패/롤백 마이그레이션. 운영자 알림 대상';

-- =====================================================
-- 5. 자체 등록 (idempotent)
--    본 파일도 마이그레이션 이력에 남긴다.
-- =====================================================
INSERT INTO tp_audit.schema_migrations (name, checksum, applied_by, duration_ms, status, notes)
VALUES ('0000_schema_migrations.sql',
        NULL,
        COALESCE(current_setting('tp.applied_by', true), session_user),
        0,
        'SUCCESS',
        '추적 테이블 자체. 본 행은 migrate_all.sh 의 자기검증용 시드.')
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- 검증 쿼리(코멘트)
-- =====================================================
-- SELECT * FROM tp_audit.v_recent_migrations;
-- SELECT * FROM tp_audit.v_failed_migrations;
-- SELECT COUNT(*) FROM tp_audit.schema_migrations WHERE status='SUCCESS';
