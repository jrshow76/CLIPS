-- =====================================================
-- TradePilot - Refresh Token 회전(rotation) 보강
-- 파일: 2026_05_add_refresh_token_rotation.sql
-- 스키마: tp_user / tp_trade
-- 설명:
--   1) SEC-004(GATE-3) — refresh 토큰 완전 회전 지원을 위한 sessions 테이블 보강.
--      - jti 식별자, 회전 체인(replaced_by_jti) 컬럼 추가.
--      - replay 탐지 시 user 단위 일괄 폐기 인덱스 최적화.
--   2) SEC-003(GATE-1) — Kill Switch 부분 실패 재시도 백그라운드를 위한
--      orders 테이블에 last_kill_switch_attempt_at / kill_switch_attempts 컬럼 추가.
-- 적용일: 2026-05-14
-- idempotent: ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS 사용
-- =====================================================

SET search_path TO tp_user, tp_trade, public;

-- =====================================================
-- 1) tp_user.sessions : Refresh Token 회전 컬럼
-- =====================================================
-- 신규 컬럼
ALTER TABLE tp_user.sessions
    ADD COLUMN IF NOT EXISTS jti                UUID            NULL;
ALTER TABLE tp_user.sessions
    ADD COLUMN IF NOT EXISTS device_id          VARCHAR(64)     NULL;
ALTER TABLE tp_user.sessions
    ADD COLUMN IF NOT EXISTS issued_at          TIMESTAMPTZ     NULL;
ALTER TABLE tp_user.sessions
    ADD COLUMN IF NOT EXISTS replaced_by_jti    UUID            NULL;

-- 기존 행에 대해 jti가 NULL이면 임의 UUID로 채워 UNIQUE 보장 (마이그레이션 안정성)
-- 운영 적용 시 사용자는 즉시 재로그인이 권장된다(기존 토큰 회전 체인 누락).
UPDATE tp_user.sessions
   SET jti = gen_random_uuid()
 WHERE jti IS NULL;

UPDATE tp_user.sessions
   SET issued_at = created_at
 WHERE issued_at IS NULL;

-- NOT NULL 제약 강화 (idempotent 처리: 컬럼이 이미 NOT NULL인 경우에도 안전)
ALTER TABLE tp_user.sessions
    ALTER COLUMN jti SET NOT NULL;

-- UNIQUE 인덱스 (jti)
CREATE UNIQUE INDEX IF NOT EXISTS uq_sessions_jti
    ON tp_user.sessions (jti);

-- (user_id, revoked_at) 인덱스 — 사용자 단위 일괄 폐기 / 활성 세션 조회 가속
CREATE INDEX IF NOT EXISTS idx_sessions_user_revoked
    ON tp_user.sessions (user_id, revoked_at);

-- (expires_at) 인덱스 — 토큰 정리 백그라운드 작업 가속
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at
    ON tp_user.sessions (expires_at);

COMMENT ON COLUMN tp_user.sessions.jti              IS 'JWT refresh 토큰의 고유 식별자 (claim jti). 매 회전마다 새 jti 발급';
COMMENT ON COLUMN tp_user.sessions.replaced_by_jti  IS '본 세션이 회전되어 발급된 후속 jti. 폐기 시 NULL이 아닌 값을 가지면 정상 회전, NULL이면 명시적 로그아웃 또는 replay 탐지에 의한 강제 폐기';
COMMENT ON COLUMN tp_user.sessions.device_id        IS '디바이스 식별자(선택). 다중 디바이스 환경에서 회전 체인 분리에 사용';
COMMENT ON COLUMN tp_user.sessions.issued_at        IS '토큰 최초 발급 시각 (created_at과 동일하지만 의미적 명시)';


-- =====================================================
-- 2) tp_trade.orders : Kill Switch 부분 실패 재시도 컬럼
-- =====================================================
ALTER TABLE tp_trade.orders
    ADD COLUMN IF NOT EXISTS last_kill_switch_attempt_at TIMESTAMPTZ NULL;
ALTER TABLE tp_trade.orders
    ADD COLUMN IF NOT EXISTS kill_switch_attempts        INTEGER     NOT NULL DEFAULT 0;

COMMENT ON COLUMN tp_trade.orders.last_kill_switch_attempt_at IS 'Kill Switch에서 cancel_order 호출이 실패한 마지막 시각. 재시도 백그라운드 작업이 5분마다 본 컬럼을 갱신한다';
COMMENT ON COLUMN tp_trade.orders.kill_switch_attempts        IS 'Kill Switch 게이트웨이 cancel_order 호출 누적 시도 횟수 (성공/실패 무관)';

-- 미해소 부분 실패 주문 빠른 조회 인덱스 (재시도 워커가 사용)
CREATE INDEX IF NOT EXISTS idx_orders_kill_switch_pending
    ON tp_trade.orders (last_kill_switch_attempt_at, status)
    WHERE last_kill_switch_attempt_at IS NOT NULL
      AND status IN ('NEW','PENDING','PARTIAL','ACCEPTED');


-- =====================================================
-- 변경 확인 쿼리 (코멘트)
-- =====================================================
-- \d+ tp_user.sessions
-- \d+ tp_trade.orders
-- SELECT indexname FROM pg_indexes WHERE schemaname='tp_user' AND tablename='sessions';
-- SELECT indexname FROM pg_indexes WHERE schemaname='tp_trade' AND tablename='orders';
