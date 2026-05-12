-- =====================================================
-- TradePilot - 사용자 도메인 DDL
-- 파일: 10_user_domain.sql
-- 스키마: tp_user
-- 포함: users, user_profiles, user_settings, otp_codes,
--       sessions, user_favorites, audit_login
-- =====================================================

SET search_path TO tp_user, public;

-- ----------------------------------------------------
-- users : 사용자 마스터
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_user.users (
    id                  BIGSERIAL       PRIMARY KEY,
    public_id           UUID            NOT NULL DEFAULT gen_random_uuid(),  -- 외부 노출용 ID
    email               CITEXT          NOT NULL,                            -- 대소문자 무시
    password_hash       VARCHAR(255)    NOT NULL,                            -- bcrypt cost>=12
    nickname            VARCHAR(50)     NOT NULL,
    phone               VARCHAR(20)     NULL,
    role                VARCHAR(20)     NOT NULL DEFAULT 'ROLE_TRADER',      -- ROLE_ADMIN/OPERATOR/TRADER_PRO/TRADER/GUEST
    trade_mode          VARCHAR(10)     NOT NULL DEFAULT 'SIM',              -- SIM | LIVE
    email_verified      BOOLEAN         NOT NULL DEFAULT FALSE,
    phone_verified      BOOLEAN         NOT NULL DEFAULT FALSE,
    disclaimer_agreed_at TIMESTAMPTZ    NULL,                                -- 자동매매 리스크 고지 동의 시각
    last_login_at       TIMESTAMPTZ     NULL,
    login_fail_count    INTEGER         NOT NULL DEFAULT 0,
    locked_until        TIMESTAMPTZ     NULL,                                -- 5회 실패 시 15분 잠금
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ     NULL,                                -- 소프트 삭제(탈퇴)
    CONSTRAINT uq_users_email      UNIQUE (email),
    CONSTRAINT uq_users_public_id  UNIQUE (public_id),
    CONSTRAINT ck_users_role       CHECK (role IN ('ROLE_ADMIN','ROLE_OPERATOR','ROLE_TRADER_PRO','ROLE_TRADER','ROLE_GUEST')),
    CONSTRAINT ck_users_trade_mode CHECK (trade_mode IN ('SIM','LIVE'))
);
COMMENT ON TABLE  tp_user.users IS '사용자 마스터. PII는 마스킹/익명화 절차 대상';
COMMENT ON COLUMN tp_user.users.public_id IS '외부 노출용 UUID (URL/API 응답)';
COMMENT ON COLUMN tp_user.users.trade_mode IS '현재 매매 모드 - SIM/LIVE';
COMMENT ON COLUMN tp_user.users.deleted_at IS '탈퇴 마킹 시각. +30일 후 익명화 배치 실행';

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON tp_user.users
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- user_profiles : 프로필 부가정보 (1:1)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_user.user_profiles (
    user_id     BIGINT          PRIMARY KEY,
    avatar_url  TEXT            NULL,
    timezone    VARCHAR(40)     NOT NULL DEFAULT 'Asia/Seoul',
    locale      VARCHAR(10)     NOT NULL DEFAULT 'ko-KR',
    extra       JSONB           NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_user_profiles_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE
);
COMMENT ON TABLE tp_user.user_profiles IS '사용자 프로필 부가정보 (아바타/타임존/로케일)';

CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON tp_user.user_profiles
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- user_settings : 알림/스케줄/테마 (1:1)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_user.user_settings (
    user_id         BIGINT          PRIMARY KEY,
    theme           VARCHAR(10)     NOT NULL DEFAULT 'light',                -- light/dark
    noti_inapp      BOOLEAN         NOT NULL DEFAULT TRUE,
    noti_email      BOOLEAN         NOT NULL DEFAULT TRUE,
    noti_telegram   BOOLEAN         NOT NULL DEFAULT FALSE,
    noti_rules      JSONB           NOT NULL DEFAULT '{}'::jsonb,            -- 이벤트별 ON/OFF/임계값
    schedule        JSONB           NOT NULL DEFAULT '{}'::jsonb,            -- 자동매매 ON/OFF 스케줄
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_user_settings_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE,
    CONSTRAINT ck_user_settings_theme CHECK (theme IN ('light','dark'))
);
COMMENT ON TABLE tp_user.user_settings IS '사용자 설정 (알림/스케줄/테마)';

CREATE TRIGGER trg_user_settings_updated_at
    BEFORE UPDATE ON tp_user.user_settings
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- otp_codes : OTP 발급 이력 (단방향 해시 저장)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_user.otp_codes (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         BIGINT          NOT NULL,
    otp_id          UUID            NOT NULL DEFAULT gen_random_uuid(),     -- 외부 식별자
    purpose         VARCHAR(30)     NOT NULL,                                -- LOGIN/SIGNUP/TRADE_MODE/PASSWORD_RESET 등
    code_hash       VARCHAR(255)    NOT NULL,                                -- 6자리 코드의 HMAC-SHA256
    channel         VARCHAR(10)     NOT NULL,                                -- SMS/EMAIL
    expires_at      TIMESTAMPTZ     NOT NULL,                                -- 발급 후 3분
    consumed_at     TIMESTAMPTZ     NULL,
    attempt_count   INTEGER         NOT NULL DEFAULT 0,                      -- 검증 시도 횟수
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_otp_user_id   FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE,
    CONSTRAINT uq_otp_otp_id    UNIQUE (otp_id),
    CONSTRAINT ck_otp_channel   CHECK (channel IN ('SMS','EMAIL')),
    CONSTRAINT ck_otp_purpose   CHECK (purpose IN ('LOGIN','SIGNUP','TRADE_MODE','PASSWORD_RESET','OTHER'))
);
COMMENT ON TABLE tp_user.otp_codes IS 'OTP 발급 이력. 7일 보관 후 삭제';

-- ----------------------------------------------------
-- sessions : Refresh Token 세션
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_user.sessions (
    id                      BIGSERIAL       PRIMARY KEY,
    user_id                 BIGINT          NOT NULL,
    refresh_token_hash      VARCHAR(255)    NOT NULL,                       -- SHA-256 해시
    user_agent              VARCHAR(255)    NULL,
    ip_address              INET            NULL,
    expires_at              TIMESTAMPTZ     NOT NULL,                       -- 7일
    revoked_at              TIMESTAMPTZ     NULL,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_sessions_user_id      FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE,
    CONSTRAINT uq_sessions_refresh_hash UNIQUE (refresh_token_hash)
);
COMMENT ON TABLE tp_user.sessions IS 'JWT Refresh Token 세션. 만료+30일 후 정리';

-- ----------------------------------------------------
-- user_favorites : 종목 즐겨찾기
--   FK는 tp_market.stocks에 의존하므로 11_market_domain.sql에서 추가
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_user.user_favorites (
    user_id     BIGINT          NOT NULL,
    stock_id    BIGINT          NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_user_favorites           PRIMARY KEY (user_id, stock_id),
    CONSTRAINT fk_user_favorites_user_id   FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE
);
COMMENT ON TABLE tp_user.user_favorites IS '사용자 즐겨찾기 종목 (FK stocks는 11_market_domain.sql에서 추가)';

-- ----------------------------------------------------
-- audit_login : 로그인/로그아웃 이력 (보안 추적)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_user.audit_login (
    id          BIGSERIAL       PRIMARY KEY,
    user_id     BIGINT          NULL,                                       -- 로그인 실패 시 NULL 가능
    event       VARCHAR(20)     NOT NULL,                                   -- LOGIN/LOGOUT/LOGIN_FAIL/LOCKED
    result      VARCHAR(10)     NOT NULL,                                   -- SUCCESS/FAIL
    ip_address  INET            NULL,
    user_agent  VARCHAR(255)    NULL,
    meta        JSONB           NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_audit_login_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE SET NULL,
    CONSTRAINT ck_audit_login_event   CHECK (event IN ('LOGIN','LOGOUT','LOGIN_FAIL','LOCKED','UNLOCK')),
    CONSTRAINT ck_audit_login_result  CHECK (result IN ('SUCCESS','FAIL'))
);
COMMENT ON TABLE tp_user.audit_login IS '로그인 감사 로그 (1년 보관)';
