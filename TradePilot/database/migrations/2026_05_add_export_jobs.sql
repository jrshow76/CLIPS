-- =====================================================
-- TradePilot - 익스포트 잡(export_jobs) 테이블 신규 생성
-- 파일: 2026_05_add_export_jobs.sql
-- 스키마: tp_trade
-- 설명: CSV/XLSX 익스포트 + S3 업로드 + 사전서명 URL 발급 이력
-- 적용일: 2026-05-14
--
-- 보관 정책:
--   - 완료 후 7일(EXPORT_TTL_HOURS=168) 경과 시 S3 객체 + 본 행 삭제 (cleanup beat)
--   - PENDING/RUNNING 상태로 1시간 이상 지나면 FAILED 처리(timeout)
--
-- 사용자 한도(서비스 계층 enforce):
--   - 사용자당 동시 PENDING/RUNNING 최대 3건
--   - 사용자당 일일 신규 요청 최대 20건
-- =====================================================

SET search_path TO tp_trade, public;

-- ----------------------------------------------------
-- export_jobs : 익스포트 잡 마스터
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_trade.export_jobs (
    id                          BIGSERIAL       PRIMARY KEY,
    public_id                   UUID            NOT NULL DEFAULT gen_random_uuid(),
    user_id                     BIGINT          NOT NULL,

    -- 익스포트 메타
    job_type                    VARCHAR(20)     NOT NULL,                       -- ORDERS/PNL/BACKTEST/SIGNALS/POSITIONS
    format                      VARCHAR(10)     NOT NULL DEFAULT 'CSV',         -- CSV/XLSX
    filter_params               JSONB           NOT NULL DEFAULT '{}'::jsonb,   -- 기간/종목/전략 등 필터

    -- 상태
    status                      VARCHAR(20)     NOT NULL DEFAULT 'PENDING',     -- PENDING/RUNNING/DONE/FAILED/EXPIRED/CANCELED
    progress_percent            SMALLINT        NOT NULL DEFAULT 0,

    -- 결과
    file_path                   TEXT            NULL,                           -- S3 key (exports/{user_id}/{public_id}.{ext})
    file_size_bytes             BIGINT          NULL,
    row_count                   BIGINT          NULL,
    download_url                TEXT            NULL,                           -- 사전서명 URL(만료 시 갱신)
    download_url_expires_at     TIMESTAMPTZ     NULL,

    -- 오류
    error_message               TEXT            NULL,

    -- 타임스탬프
    created_at                  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    started_at                  TIMESTAMPTZ     NULL,
    completed_at                TIMESTAMPTZ     NULL,
    expires_at                  TIMESTAMPTZ     NULL,                           -- S3 파일 보관 만료 시점(완료 후 7일)

    CONSTRAINT uq_export_jobs_public_id UNIQUE (public_id),
    CONSTRAINT fk_export_jobs_user      FOREIGN KEY (user_id)
        REFERENCES tp_user.users(id) ON DELETE CASCADE,
    CONSTRAINT ck_export_jobs_type      CHECK (job_type IN ('ORDERS','PNL','BACKTEST','SIGNALS','POSITIONS')),
    CONSTRAINT ck_export_jobs_format    CHECK (format IN ('CSV','XLSX')),
    CONSTRAINT ck_export_jobs_status    CHECK (status IN ('PENDING','RUNNING','DONE','FAILED','EXPIRED','CANCELED')),
    CONSTRAINT ck_export_jobs_progress  CHECK (progress_percent BETWEEN 0 AND 100)
);

COMMENT ON TABLE  tp_trade.export_jobs IS '익스포트(CSV/XLSX) 잡 이력. S3 업로드 + 사전서명 URL.';
COMMENT ON COLUMN tp_trade.export_jobs.job_type IS 'ORDERS: 거래내역, PNL: 일별손익, BACKTEST: 백테스트, SIGNALS: 시그널이력, POSITIONS: 보유종목';
COMMENT ON COLUMN tp_trade.export_jobs.file_path IS 'S3 object key. exports/{user_id}/{public_id}.{ext}';
COMMENT ON COLUMN tp_trade.export_jobs.download_url IS 'S3 presigned URL. 기본 TTL 1시간. 만료 후 download 호출 시 자동 갱신.';
COMMENT ON COLUMN tp_trade.export_jobs.expires_at IS 'S3 파일 보관 만료 시점(완료 7일 후). cleanup 잡이 본 행과 S3 객체를 삭제.';

-- updated_at 자동 갱신
DROP TRIGGER IF EXISTS trg_export_jobs_updated_at ON tp_trade.export_jobs;
CREATE TRIGGER trg_export_jobs_updated_at
    BEFORE UPDATE ON tp_trade.export_jobs
    FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

-- ----------------------------------------------------
-- 인덱스
-- ----------------------------------------------------
-- 사용자별 이력 페이지: (user_id, created_at DESC)
CREATE INDEX IF NOT EXISTS idx_export_jobs_user_created
    ON tp_trade.export_jobs (user_id, created_at DESC);

-- 한도 체크(동시 PENDING/RUNNING): 상태 + 사용자 부분 인덱스
CREATE INDEX IF NOT EXISTS idx_export_jobs_active_per_user
    ON tp_trade.export_jobs (user_id, status)
    WHERE status IN ('PENDING','RUNNING');

-- cleanup 잡(만료 스캔): (expires_at) 부분 인덱스
CREATE INDEX IF NOT EXISTS idx_export_jobs_expires
    ON tp_trade.export_jobs (expires_at)
    WHERE status = 'DONE' AND expires_at IS NOT NULL;

-- 상태 폴링(워커 픽업): (status, created_at)
CREATE INDEX IF NOT EXISTS idx_export_jobs_status_created
    ON tp_trade.export_jobs (status, created_at);

-- =====================================================
-- 검증 쿼리(코멘트)
-- =====================================================
-- SELECT status, COUNT(*) FROM tp_trade.export_jobs GROUP BY status;
-- SELECT user_id, COUNT(*)
--   FROM tp_trade.export_jobs
--   WHERE status IN ('PENDING','RUNNING')
--   GROUP BY user_id;
