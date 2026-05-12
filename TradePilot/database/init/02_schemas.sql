-- =====================================================
-- TradePilot - 스키마(도메인) 생성
-- 파일: 02_schemas.sql
-- 도메인 분리로 권한·백업·파티션 격리 가능
-- =====================================================

-- 사용자/인증/세션 도메인
CREATE SCHEMA IF NOT EXISTS tp_user;
COMMENT ON SCHEMA tp_user IS 'TradePilot 사용자/인증/세션/즐겨찾기 도메인';

-- 시장 데이터(종목/시세/섹터) 도메인
CREATE SCHEMA IF NOT EXISTS tp_market;
COMMENT ON SCHEMA tp_market IS 'TradePilot 종목 마스터/시세/섹터/지수 도메인';

-- 분석(지표 캐시/추천/시그널/ML 예측) 도메인
CREATE SCHEMA IF NOT EXISTS tp_analysis;
COMMENT ON SCHEMA tp_analysis IS 'TradePilot 지표/추천/시그널/ML 예측 도메인';

-- 매매(전략/주문/체결/포지션/한도/Kill Switch/백테스트) 도메인
CREATE SCHEMA IF NOT EXISTS tp_trade;
COMMENT ON SCHEMA tp_trade IS 'TradePilot 전략/주문/체결/포트폴리오/백테스트 도메인';

-- 알림 도메인
CREATE SCHEMA IF NOT EXISTS tp_notify;
COMMENT ON SCHEMA tp_notify IS 'TradePilot 알림 큐/채널/룰 도메인';

-- 감사 도메인 (append-only)
CREATE SCHEMA IF NOT EXISTS tp_audit;
COMMENT ON SCHEMA tp_audit IS 'TradePilot 감사 로그(append-only) 도메인';

-- 기본 search_path 설정 (이 DB에 접속하는 세션의 기본 스키마 탐색 순서)
-- 운영 시에는 역할별 search_path를 별도 설정하는 것을 권장한다.
ALTER DATABASE CURRENT SET search_path TO tp_user, tp_market, tp_analysis, tp_trade, tp_notify, tp_audit, public;

-- =====================================================
-- 공통 트리거 함수: updated_at 자동 갱신
-- 비즈니스 테이블의 BEFORE UPDATE 트리거에서 사용
-- =====================================================
CREATE OR REPLACE FUNCTION public.fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION public.fn_set_updated_at() IS 'BEFORE UPDATE 트리거에서 updated_at을 현재 시각으로 자동 갱신';
