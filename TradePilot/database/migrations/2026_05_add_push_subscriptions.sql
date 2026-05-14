-- =====================================================
-- TradePilot - Web Push 구독 테이블 신규 생성
-- 파일: 2026_05_add_push_subscriptions.sql
-- 스키마: tp_user
-- 설명: PWA / Web Push subscription endpoint + 키 매핑
-- 적용일: 2026-05-14
--
-- 보관 정책:
--   - 410 Gone / 404 응답 시 즉시 삭제 (서비스 계층 처리)
--   - last_used_at 이 90일 이상 지난 행은 정리 잡으로 비활성화
--   - expires_at 이 NULL 이 아닌 경우 만료 시점 도래 시 제거
--
-- 보안:
--   - p256dh_key / auth_key 는 클라이언트의 공개 정보(엔드포인트 push 서버에서만 사용)
--   - 평문 저장 허용. 다만 endpoint 자체가 추적 식별자가 되므로 DB 권한 분리는 유지
--   - GDPR/PIPA: 회원 탈퇴 시 ON DELETE CASCADE 로 동시 제거
-- =====================================================

SET search_path TO tp_user, public;

-- ----------------------------------------------------
-- push_subscriptions
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_user.push_subscriptions (
    id                  BIGSERIAL       PRIMARY KEY,
    user_id             BIGINT          NOT NULL,

    -- Push Service endpoint URL (https://...)
    endpoint            TEXT            NOT NULL,

    -- VAPID 암호화에 사용되는 클라이언트 공개키 / 인증 시크릿
    p256dh_key          TEXT            NOT NULL,
    auth_key            TEXT            NOT NULL,

    -- 보조 메타
    user_agent          TEXT,                                        -- UA 문자열 (디바이스 추적)
    expires_at          TIMESTAMPTZ,                                 -- pushManager 가 보고한 만료 시각

    -- 라이프사이클
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_used_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- 활성 상태 (soft disable; 410/404 시 row 즉시 삭제이지만 일시 비활성도 지원)
    active              BOOLEAN         NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_push_sub_user
        FOREIGN KEY (user_id) REFERENCES tp_user.users (id) ON DELETE CASCADE,

    -- 동일 사용자의 동일 endpoint 중복 방지
    CONSTRAINT uq_push_sub_user_endpoint UNIQUE (user_id, endpoint)
);

COMMENT ON TABLE  tp_user.push_subscriptions IS 'Web Push (PWA) subscription endpoint 매핑';
COMMENT ON COLUMN tp_user.push_subscriptions.endpoint    IS 'Push Service endpoint URL (FCM/APNs/Mozilla)';
COMMENT ON COLUMN tp_user.push_subscriptions.p256dh_key  IS 'P-256 공개키 (base64url)';
COMMENT ON COLUMN tp_user.push_subscriptions.auth_key    IS '인증 시크릿 (base64url)';
COMMENT ON COLUMN tp_user.push_subscriptions.expires_at  IS '브라우저가 제공한 만료 시각 (없으면 NULL)';

-- ----------------------------------------------------
-- 인덱스
-- ----------------------------------------------------
-- user_id 별 활성 endpoint 조회 (발송 시)
CREATE INDEX IF NOT EXISTS idx_push_sub_user_active
    ON tp_user.push_subscriptions (user_id)
    WHERE active = TRUE;

-- last_used_at 기준 정리 잡 / 만료 처리
CREATE INDEX IF NOT EXISTS idx_push_sub_last_used
    ON tp_user.push_subscriptions (last_used_at);

-- endpoint 직접 lookup (해제 시)
CREATE INDEX IF NOT EXISTS idx_push_sub_endpoint
    ON tp_user.push_subscriptions USING HASH (md5(endpoint));

-- ----------------------------------------------------
-- 권한 (애플리케이션 롤만 접근, 관리자/감사는 read-only)
-- ----------------------------------------------------
-- 99_grants.sql 패턴과 일관되게 부여:
--   GRANT SELECT, INSERT, UPDATE, DELETE ON tp_user.push_subscriptions TO tradepilot_app;
--   GRANT USAGE ON SEQUENCE tp_user.push_subscriptions_id_seq TO tradepilot_app;
-- 운영 시 별도 변경 스크립트로 적용한다.
