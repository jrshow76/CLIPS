-- =====================================================================
-- Tulip+ IAM Service — V1 초기 스키마 (Sprint 1-B)
-- ---------------------------------------------------------------------
-- 1) Keycloak User(sub) ↔ 내부 user_id 매핑 (iam_user_link)
-- 2) JTI 블랙리스트 영구 백업 (iam_token_blacklist) — Redis 가 주 저장소
-- 3) Refresh 토큰 감사로그 (iam_refresh_audit) — 보존 1년
--
-- RLS 정책은 멀티테넌트 도메인 데이터(member/circulation 등)에 적용되며,
-- iam_* 테이블은 전역(테넌트 비종속) 또는 tenant_id 컬럼 보유 시 부분 적용한다.
-- 본 마이그레이션에서는 platform 영역으로 두며 RLS 적용은 1-C 에서 검토한다.
-- =====================================================================

CREATE TABLE IF NOT EXISTS iam_user_link (
    user_id           VARCHAR(64)  NOT NULL,
    kc_sub            VARCHAR(64)  NOT NULL,
    tenant_id         VARCHAR(64),
    default_branch_id VARCHAR(64),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_iam_user_link PRIMARY KEY (user_id),
    CONSTRAINT uq_iam_user_link_kc_sub UNIQUE (kc_sub)
);
COMMENT ON TABLE  iam_user_link IS 'Keycloak sub 와 Tulip 내부 user_id 매핑';
COMMENT ON COLUMN iam_user_link.tenant_id IS '소속 테넌트 (NULL = 플랫폼 관리자)';

CREATE INDEX IF NOT EXISTS idx_iam_user_link_tenant ON iam_user_link (tenant_id);

CREATE TABLE IF NOT EXISTS iam_token_blacklist (
    jti        VARCHAR(64)  NOT NULL,
    expires_at TIMESTAMPTZ  NOT NULL,
    reason     VARCHAR(32)  NOT NULL DEFAULT 'revoked',
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_iam_token_blacklist PRIMARY KEY (jti)
);
COMMENT ON TABLE iam_token_blacklist IS 'JTI 블랙리스트 영구 백업 (운영 분석·복원용). 실시간 검증은 Redis 사용.';
CREATE INDEX IF NOT EXISTS idx_iam_token_blacklist_exp ON iam_token_blacklist (expires_at);

CREATE TABLE IF NOT EXISTS iam_refresh_audit (
    id         BIGSERIAL    NOT NULL,
    user_id    VARCHAR(64),
    action     VARCHAR(16)  NOT NULL,  -- issue / rotate / revoke
    ip         VARCHAR(64),
    ua         TEXT,
    at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_iam_refresh_audit PRIMARY KEY (id)
);
COMMENT ON TABLE iam_refresh_audit IS 'Refresh 토큰 발급·회전·취소 감사로그 (보존 1년)';
CREATE INDEX IF NOT EXISTS idx_iam_refresh_audit_user_at ON iam_refresh_audit (user_id, at DESC);
CREATE INDEX IF NOT EXISTS idx_iam_refresh_audit_at ON iam_refresh_audit (at DESC);

-- ---------------------------------------------------------------------
-- 데모 사용자 매핑 (개발 환경 한정)
-- Keycloak realm import 시 자동 생성되는 sub 가 매번 다르므로
-- 운영에서는 본 INSERT 를 사용하지 않는다. 본 행은 비어 있어도 무방.
-- ---------------------------------------------------------------------
-- 예: INSERT INTO iam_user_link(user_id, kc_sub, tenant_id, default_branch_id) VALUES
--      ('librarian-demo-1', 'librarian-kc-sub', 'demo-tenant-1', 'demo-tenant-1-main');
