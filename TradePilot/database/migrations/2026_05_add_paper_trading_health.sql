-- =====================================================
-- TradePilot - 모의투자 5영업일 헬스체크 자동 보고
-- 파일: 2026_05_add_paper_trading_health.sql
-- 스키마: tp_audit
-- 작성자: BackendDev (E2)
-- 작성일: 2026-05-15
--
-- 목적:
--   security/76_go_decision_report.md "운영 진입 D-1 조건" 충족을 위해
--   CREON 모의투자(paper) 환경에서 5영업일 연속 안정성 보고서를 자동
--   생성/보관한다. 일일 점수(0~100) + GO/NO-GO 판정과 항목별 결과를
--   JSONB로 보관하여 운영자 대시보드와 5영업일 GO 판정 API가 활용한다.
--
-- 보관 정책:
--   - 운영 진입 후에도 30일은 보존(과거 추세 비교용)
--   - 별도 archive(or partition)는 본 마이그레이션 범위 아님
--
-- idempotent:
--   - CREATE TABLE IF NOT EXISTS / CREATE OR REPLACE VIEW / IF NOT EXISTS 인덱스
-- =====================================================

CREATE SCHEMA IF NOT EXISTS tp_audit;

SET search_path TO tp_audit, public;

-- ----------------------------------------------------
-- paper_trading_health_daily : 일일 헬스체크 결과
-- ----------------------------------------------------
CREATE TABLE IF NOT EXISTS tp_audit.paper_trading_health_daily (
    id              BIGSERIAL       PRIMARY KEY,
    check_date      DATE            NOT NULL,
    env             VARCHAR(20)     NOT NULL DEFAULT 'paper',

    -- 종합 판정
    overall_status  VARCHAR(20)     NOT NULL,        -- PASS / WARN / FAIL
    score           SMALLINT        NOT NULL,        -- 0 ~ 100

    -- 항목별 결과(배열) + 핵심 KPI
    --   checks: [{name, category, severity, status, value, threshold, message}, ...]
    --   kpis  : {order_count, signal_count, fill_fail_rate, kill_switch_count, live_users, ...}
    checks          JSONB           NOT NULL DEFAULT '[]'::jsonb,
    kpis            JSONB           NOT NULL DEFAULT '{}'::jsonb,

    -- 발견 이슈 수 (집계 캐시용: 뷰/쿼리에서 활용)
    failed_count    SMALLINT        NOT NULL DEFAULT 0,
    warn_count      SMALLINT        NOT NULL DEFAULT 0,

    -- 발송 결과(이메일/Slack)
    sent_email      BOOLEAN         NOT NULL DEFAULT FALSE,
    sent_slack      BOOLEAN         NOT NULL DEFAULT FALSE,
    sent_error      TEXT            NULL,

    -- 타임스탬프
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_paper_health_daily UNIQUE (env, check_date),
    CONSTRAINT ck_paper_health_status CHECK (overall_status IN ('PASS','WARN','FAIL')),
    CONSTRAINT ck_paper_health_score  CHECK (score BETWEEN 0 AND 100),
    CONSTRAINT ck_paper_health_env    CHECK (env IN ('paper','live'))
);

COMMENT ON TABLE  tp_audit.paper_trading_health_daily IS 'CREON 모의투자 일일 헬스체크 결과. 운영 진입 D-1 5영업일 검증 근거.';
COMMENT ON COLUMN tp_audit.paper_trading_health_daily.check_date     IS '점검 일자(KST 영업일 기준).';
COMMENT ON COLUMN tp_audit.paper_trading_health_daily.overall_status IS 'PASS(>=85, critical 모두 PASS) / WARN(70~84) / FAIL(<70 또는 critical FAIL 1건+)';
COMMENT ON COLUMN tp_audit.paper_trading_health_daily.score          IS '가중 평균 점수 0~100 (매매40+서비스30+보안15+성능10+인프라5).';
COMMENT ON COLUMN tp_audit.paper_trading_health_daily.checks         IS '항목별 결과 배열 (서비스/매매/인프라/보안/성능).';
COMMENT ON COLUMN tp_audit.paper_trading_health_daily.kpis           IS '주요 KPI: order_count, signal_count, fill_fail_rate, kill_switch_count, live_users 등.';

-- updated_at 자동 갱신 트리거 (다른 마이그레이션에서 정의한 공용 함수 활용)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'fn_set_updated_at'
    ) THEN
        DROP TRIGGER IF EXISTS trg_paper_health_updated_at ON tp_audit.paper_trading_health_daily;
        CREATE TRIGGER trg_paper_health_updated_at
            BEFORE UPDATE ON tp_audit.paper_trading_health_daily
            FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();
    END IF;
END$$;

-- ----------------------------------------------------
-- 인덱스
-- ----------------------------------------------------
-- 최신 N건 조회: (env, check_date DESC)
CREATE INDEX IF NOT EXISTS idx_paper_health_env_date_desc
    ON tp_audit.paper_trading_health_daily (env, check_date DESC);

-- 실패/경고 추출(추세 분석): (env, overall_status, check_date)
CREATE INDEX IF NOT EXISTS idx_paper_health_status
    ON tp_audit.paper_trading_health_daily (env, overall_status, check_date DESC);

-- ----------------------------------------------------
-- 5영업일 누적 뷰 : v_paper_trading_health_5d
--   - 환경별 최신 5개 행만 노출 (영업일 자동 필터링 — 데이터는 평일에만 적재됨)
--   - 운영자 대시보드/관리자 API 가 사용
-- ----------------------------------------------------
CREATE OR REPLACE VIEW tp_audit.v_paper_trading_health_5d AS
WITH ranked AS (
    SELECT
        h.*,
        ROW_NUMBER() OVER (PARTITION BY env ORDER BY check_date DESC) AS rn
    FROM tp_audit.paper_trading_health_daily h
)
SELECT
    id,
    check_date,
    env,
    overall_status,
    score,
    failed_count,
    warn_count,
    checks,
    kpis,
    sent_email,
    sent_slack,
    sent_error,
    created_at,
    updated_at
FROM ranked
WHERE rn <= 5;

COMMENT ON VIEW tp_audit.v_paper_trading_health_5d IS '환경별 최신 5영업일 헬스체크 결과 (대시보드/GO 판정용).';

-- =====================================================
-- 검증 쿼리 (운영자 참고)
-- =====================================================
-- 최근 5영업일 현황:
--   SELECT check_date, overall_status, score, failed_count, warn_count
--   FROM   tp_audit.v_paper_trading_health_5d
--   WHERE  env = 'paper'
--   ORDER  BY check_date DESC;
--
-- 5영업일 누적 GO 판정 (PASS >= 4일 AND 평균 점수 >= 80):
--   SELECT
--       COUNT(*) FILTER (WHERE overall_status = 'PASS') AS pass_days,
--       ROUND(AVG(score)::numeric, 1)                    AS avg_score,
--       CASE WHEN COUNT(*) = 5
--             AND COUNT(*) FILTER (WHERE overall_status = 'PASS') >= 4
--             AND AVG(score) >= 80 THEN 'GO'
--            ELSE 'NO_GO' END                            AS decision
--   FROM tp_audit.v_paper_trading_health_5d
--   WHERE env = 'paper';
