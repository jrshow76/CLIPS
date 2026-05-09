-- ============================================================
-- V001: users 테이블 생성
-- 서비스 사용자 기본 정보 저장 (이메일/비밀번호 인증, 소프트 딜리트)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- gen_random_uuid() 사용

CREATE TABLE users (
    id                UUID          NOT NULL DEFAULT gen_random_uuid(),
    email             VARCHAR(255)  NOT NULL,
    password_hash     VARCHAR(255)  NOT NULL,
    nickname          VARCHAR(20)   NOT NULL,
    profile_image_url TEXT,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    deleted_at        TIMESTAMPTZ,

    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT chk_users_email_length    CHECK (char_length(email) <= 255),
    CONSTRAINT chk_users_nickname_length CHECK (char_length(nickname) BETWEEN 2 AND 20)
);

COMMENT ON TABLE  users                   IS '사용자 계정 테이블';
COMMENT ON COLUMN users.id                IS 'PK - UUID (순차 ID 노출 방지)';
COMMENT ON COLUMN users.email             IS '로그인 ID (이메일 형식, 논리 삭제 계정 포함 UNIQUE)';
COMMENT ON COLUMN users.password_hash     IS 'bcrypt 해시 비밀번호 (cost factor 10 이상)';
COMMENT ON COLUMN users.nickname          IS '닉네임 (2~20자)';
COMMENT ON COLUMN users.profile_image_url IS '프로필 이미지 URL (CDN 경로)';
COMMENT ON COLUMN users.deleted_at        IS '탈퇴일시 (NULL = 정상 계정, Soft Delete)';

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION fn_update_timestamp()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
