-- =====================================================
-- TradePilot - PostgreSQL 확장(Extension) 초기화
-- 파일: 01_extensions.sql
-- 실행 권한: superuser 또는 createdb 권한
-- 적용 대상: 신규 DB 초기 1회
-- =====================================================

-- pgcrypto : gen_random_uuid(), digest(), crypt() 등 암호화 함수 제공
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- citext : 대소문자 무시 텍스트(이메일 컬럼용)
CREATE EXTENSION IF NOT EXISTS citext;

-- pg_trgm : 부분 문자열 검색(종목명 자동완성)용 trigram 인덱스
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- btree_gin : GIN 인덱스에서 일반 데이터타입 결합 사용
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- btree_gist : 범위/배제 제약 등에 활용
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- pg_stat_statements : 쿼리 통계(슬로우쿼리 분석 필수)
-- 주의: postgresql.conf 에 shared_preload_libraries='pg_stat_statements' 사전 등록 필요
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 활성화된 확장 확인용 코멘트
-- SELECT extname, extversion FROM pg_extension ORDER BY extname;
