-- =====================================================
-- TradePilot - 알림 도메인 DDL
-- 파일: 15_notification_domain.sql
-- 스키마: tp_notify
-- 포함: notifications(파티션), notification_channels, alert_rules
-- 그리고 감사(tp_audit) 테이블도 본 파일에서 함께 생성
-- =====================================================

SET search_path TO tp_notify, public;

-- ----------------------------------------------------
-- notifications : 알림 큐 (월별 RANGE 파티셔닝)
--   90일 보관, 읽음 처리 후 30일
--   파티션 자식은 21_partitioning.sql에서 생성
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_notify.notifications (
    id              BIGSERIAL       NOT NULL,
    user_id         BIGINT          NOT NULL,
    event_type      VARCHAR(50)     NOT NULL,                                -- SIGNAL/ORDER_FILLED/KILL_SWITCH/MODE_CHANGE/CREON_ERROR 등
    priority        VARCHAR(10)     NOT NULL DEFAULT 'NORMAL',               -- CRITICAL/HIGH/NORMAL/LOW
    channel         VARCHAR(20)     NOT NULL,                                -- INAPP/EMAIL/TELEGRAM
    title           VARCHAR(200)    NOT NULL,
    body            TEXT            NULL,
    payload         JSONB           NOT NULL DEFAULT '{}'::jsonb,
    read            BOOLEAN         NOT NULL DEFAULT FALSE,
    read_at         TIMESTAMPTZ     NULL,
    sent_at         TIMESTAMPTZ     NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_notifications      PRIMARY KEY (id, created_at),
    CONSTRAINT ck_notifications_pri  CHECK (priority IN ('CRITICAL','HIGH','NORMAL','LOW')),
    CONSTRAINT ck_notifications_ch   CHECK (channel IN ('INAPP','EMAIL','TELEGRAM','SMS'))
) PARTITION BY RANGE (created_at);
COMMENT ON TABLE tp_notify.notifications IS '알림 큐 (월별 파티셔닝, 90일 보관)';

ALTER TABLE tp_notify.notifications
    ADD CONSTRAINT fk_notifications_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE;

-- ----------------------------------------------------
-- notification_channels : 사용자 채널 설정
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_notify.notification_channels (
    user_id             BIGINT          PRIMARY KEY,
    inapp_enabled       BOOLEAN         NOT NULL DEFAULT TRUE,
    email_enabled       BOOLEAN         NOT NULL DEFAULT TRUE,
    telegram_enabled    BOOLEAN         NOT NULL DEFAULT FALSE,
    telegram_chat_id    VARCHAR(50)     NULL,
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_noti_channels_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE
);
COMMENT ON TABLE tp_notify.notification_channels IS '사용자별 알림 채널 활성 여부';

CREATE TRIGGER trg_noti_channels_updated_at
    BEFORE UPDATE ON tp_notify.notification_channels
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- alert_rules : 사용자 알림 룰 (이벤트 + 조건 + 우선순위)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_notify.alert_rules (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         BIGINT          NOT NULL,
    event_type      VARCHAR(50)     NOT NULL,
    condition       JSONB           NOT NULL DEFAULT '{}'::jsonb,            -- 예: {"min_confidence":"HIGH"}
    priority        VARCHAR(10)     NOT NULL DEFAULT 'NORMAL',
    active          BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_alert_rules_user_id   FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE CASCADE,
    CONSTRAINT ck_alert_rules_priority  CHECK (priority IN ('CRITICAL','HIGH','NORMAL','LOW'))
);
COMMENT ON TABLE tp_notify.alert_rules IS '사용자 알림 룰';

CREATE TRIGGER trg_alert_rules_updated_at
    BEFORE UPDATE ON tp_notify.alert_rules
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- =====================================================
-- 감사 도메인 (tp_audit)
-- =====================================================

SET search_path TO tp_audit, public;

-- ----------------------------------------------------
-- audit_trade_mode : SIM ↔ LIVE 전환 이력
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_audit.audit_trade_mode (
    id          BIGSERIAL       PRIMARY KEY,
    user_id     BIGINT          NOT NULL,
    from_mode   VARCHAR(10)     NULL,
    to_mode     VARCHAR(10)     NOT NULL,
    trigger     VARCHAR(30)     NOT NULL,                                    -- USER/SYSTEM/DAILY_LOSS/KILL_SWITCH/CREON 등
    meta        JSONB           NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_atm_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE RESTRICT,
    CONSTRAINT ck_atm_to_mode CHECK (to_mode IN ('SIM','LIVE'))
);
COMMENT ON TABLE tp_audit.audit_trade_mode IS '매매 모드 전환 감사 로그 (append-only, 10년)';

-- ----------------------------------------------------
-- audit_order_history : 주문 상태 변경 이력 (월별 파티셔닝)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_audit.audit_order_history (
    id              BIGSERIAL       NOT NULL,
    order_id        BIGINT          NOT NULL,
    from_status     VARCHAR(20)     NULL,
    to_status       VARCHAR(20)     NOT NULL,
    diff            JSONB           NOT NULL DEFAULT '{}'::jsonb,            -- 변경된 필드 스냅샷
    actor_user_id   BIGINT          NULL,                                    -- 변경 주체(NULL=시스템)
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_audit_order_history PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);
COMMENT ON TABLE tp_audit.audit_order_history IS '주문 상태 변경 감사 로그 (월별 파티셔닝, 10년)';

-- ----------------------------------------------------
-- audit_role_change : 권한 변경 이력
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_audit.audit_role_change (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         BIGINT          NOT NULL,
    from_role       VARCHAR(20)     NULL,
    to_role         VARCHAR(20)     NOT NULL,
    actor_user_id   BIGINT          NULL,
    reason          TEXT            NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_arc_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE RESTRICT
);
COMMENT ON TABLE tp_audit.audit_role_change IS '권한 변경 감사 로그';

-- ----------------------------------------------------
-- audit_risk_event : 리스크 이벤트 (한도초과/강제청산/슬리피지 등)
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_audit.audit_risk_event (
    id          BIGSERIAL       PRIMARY KEY,
    user_id     BIGINT          NULL,                                        -- 시스템 이벤트는 NULL
    event_type  VARCHAR(30)     NOT NULL,                                    -- LIMIT_EXCEED/FORCED_LIQUIDATION/SLIPPAGE/CIRCUIT_BREAK
    severity    VARCHAR(10)     NOT NULL DEFAULT 'WARN',                     -- INFO/WARN/CRITICAL
    detail      JSONB           NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT fk_are_user_id FOREIGN KEY (user_id) REFERENCES tp_user.users(id) ON DELETE SET NULL,
    CONSTRAINT ck_are_severity CHECK (severity IN ('INFO','WARN','CRITICAL'))
);
COMMENT ON TABLE tp_audit.audit_risk_event IS '리스크 이벤트 감사 로그 (10년)';
