-- =====================================================
-- TradePilot - 다증권사(Broker) 설정 보강
-- 파일: 2026_05_add_broker_settings.sql
-- 스키마: tp_user
-- 설명:
--   D4 — 다증권사 어댑터(KIS / 키움 / CREON) 도입을 위한 컬럼/테이블 추가.
--   1) tp_user.users 에 preferred_broker, broker_credentials 컬럼 추가
--   2) tp_user.broker_status 신규 테이블 (가용성/헬스 모니터링)
--   3) 인덱스 + 코멘트
-- 적용일: 2026-05-14
-- idempotent: ADD COLUMN IF NOT EXISTS / CREATE TABLE IF NOT EXISTS
-- =====================================================

SET search_path TO tp_user, public;

-- =====================================================
-- 1) tp_user.users : 선호 증권사 + 암호화된 자격증명
-- =====================================================
ALTER TABLE tp_user.users
    ADD COLUMN IF NOT EXISTS preferred_broker    VARCHAR(20)  NOT NULL DEFAULT 'CREON';

ALTER TABLE tp_user.users
    ADD COLUMN IF NOT EXISTS broker_credentials  JSONB        NOT NULL DEFAULT '{}'::jsonb;

-- 값 제약: 등록된 증권사만 허용
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_schema='tp_user' AND constraint_name='ck_users_preferred_broker'
    ) THEN
        ALTER TABLE tp_user.users
            ADD CONSTRAINT ck_users_preferred_broker
            CHECK (preferred_broker IN ('CREON','KIS','KIWOOM'));
    END IF;
END$$;

COMMENT ON COLUMN tp_user.users.preferred_broker
    IS '사용자 선호 증권사 (CREON / KIS / KIWOOM). 미설정 시 시스템 기본 CREON.';

COMMENT ON COLUMN tp_user.users.broker_credentials
    IS '증권사별 암호화된 자격증명 JSON. AES-256-GCM 토큰 보관.
        예: {"KIS": {"appkey_enc": "...", "appsecret_enc": "...", "account_no": "...", "account_prod_cd": "01", "connected_at": "..."},
             "KIWOOM": {"account_no": "...", "connected_at": "..."}}.
        평문 비밀은 절대 저장하지 않는다.';


-- =====================================================
-- 2) tp_user.broker_status : 증권사별 가용성 모니터링
-- =====================================================
CREATE TABLE IF NOT EXISTS tp_user.broker_status (
    broker          VARCHAR(20)  PRIMARY KEY,
    available       BOOLEAN      NOT NULL DEFAULT TRUE,
    last_check_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_error      TEXT         NULL,
    active_users    INTEGER      NOT NULL DEFAULT 0,
    sla_p99_ms      INTEGER      NULL,
    note            TEXT         NULL,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_broker_status_broker CHECK (broker IN ('CREON','KIS','KIWOOM'))
);

COMMENT ON TABLE  tp_user.broker_status
    IS '증권사별 가용성 / 헬스 모니터링. 운영 화면에서 fallback 판단 보조.';
COMMENT ON COLUMN tp_user.broker_status.available    IS '현재 가용 여부 (헬스비트 기반).';
COMMENT ON COLUMN tp_user.broker_status.active_users IS '해당 증권사를 preferred 로 사용 중인 사용자 수.';
COMMENT ON COLUMN tp_user.broker_status.sla_p99_ms   IS '최근 10분 P99 응답 ms (모니터링 집계).';

-- 트리거 (updated_at)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc WHERE proname='fn_set_updated_at'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname='trg_broker_status_updated_at'
    ) THEN
        EXECUTE 'CREATE TRIGGER trg_broker_status_updated_at
                 BEFORE UPDATE ON tp_user.broker_status
                 FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at()';
    END IF;
END$$;

-- 기본 행 시드 (idempotent)
INSERT INTO tp_user.broker_status (broker, available, note)
VALUES
    ('CREON',  TRUE,  '대신증권 Plus (Windows COM 게이트웨이)'),
    ('KIS',    TRUE,  '한국투자증권 OpenAPI (REST/WebSocket)'),
    ('KIWOOM', TRUE,  '키움증권 OpenAPI+ (Windows COM 게이트웨이)')
ON CONFLICT (broker) DO NOTHING;


-- =====================================================
-- 3) 인덱스
-- =====================================================
-- 사용자별 preferred broker 통계용 (admin 화면, broker_status.active_users 집계)
CREATE INDEX IF NOT EXISTS ix_users_preferred_broker
    ON tp_user.users (preferred_broker)
    WHERE deleted_at IS NULL;
