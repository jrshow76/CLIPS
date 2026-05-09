-- ============================================================
-- V004: refresh_tokens 테이블 생성
-- JWT Refresh Token 서버 측 레코드 관리 (토큰 탈취 방지용 해시 저장)
-- ============================================================

CREATE TABLE refresh_tokens (
    id          BIGSERIAL    NOT NULL,
    user_id     UUID         NOT NULL,
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  TIMESTAMPTZ  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    revoked_at  TIMESTAMPTZ,

    CONSTRAINT pk_refresh_tokens       PRIMARY KEY (id),
    CONSTRAINT uq_refresh_token_hash   UNIQUE (token_hash),
    CONSTRAINT fk_rt_user              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_rt_expires_at       CHECK (expires_at > created_at)
);

COMMENT ON TABLE  refresh_tokens            IS 'JWT Refresh Token 관리 테이블';
COMMENT ON COLUMN refresh_tokens.token_hash IS 'SHA-256 해시된 토큰 (DB 탈취 시 재사용 방지)';
COMMENT ON COLUMN refresh_tokens.expires_at IS '만료일시 (발급 시 +7일)';
COMMENT ON COLUMN refresh_tokens.revoked_at IS '무효화 일시 (NULL = 유효, 로그아웃 시 설정)';
