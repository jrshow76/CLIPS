-- =====================================================================
-- Tulip+ — PostgreSQL 초기 확장 설치
-- (docker-entrypoint-initdb.d 는 첫 기동 시 1회만 실행됨)
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 운영 계정 생성 (개발 환경)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tulip_app') THEN
    CREATE ROLE tulip_app LOGIN PASSWORD 'tulip_app';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE tulip TO tulip_app;
GRANT USAGE, CREATE ON SCHEMA public TO tulip_app;
