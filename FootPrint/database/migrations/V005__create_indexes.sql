-- ============================================================
-- V005: 인덱스 생성
-- 각 인덱스는 실제 API 쿼리 기반 근거를 주석으로 명시
-- ============================================================

-- ── users ──────────────────────────────────────────────────
-- 로그인 시 매번 실행: SELECT * FROM users WHERE email = $1 AND deleted_at IS NULL
-- 부분 인덱스로 논리 삭제 계정 제외 → 인덱스 크기 최소화
CREATE UNIQUE INDEX idx_users_email_active
    ON users (email)
    WHERE deleted_at IS NULL;

-- ── categories ─────────────────────────────────────────────
-- C-01 카테고리 목록 조회: WHERE user_id = $1 OR is_default = TRUE
CREATE INDEX idx_categories_user_id
    ON categories (user_id);

-- 사용자별 카테고리명 중복 방지 (NULL user_id 제외)
CREATE UNIQUE INDEX uq_categories_user_name
    ON categories (user_id, name)
    WHERE user_id IS NOT NULL;

-- ── places ─────────────────────────────────────────────────
-- P-01 장소 목록 조회 (미삭제 장소): WHERE user_id = $1 AND deleted_at IS NULL ORDER BY visited_at DESC
-- 부분 인덱스로 삭제된 장소 제외, visited_at DESC 정렬 포함
CREATE INDEX idx_places_user_visited
    ON places (user_id, visited_at DESC)
    WHERE deleted_at IS NULL;

-- P-04 지도 뷰포트 쿼리: WHERE user_id = $1 AND latitude BETWEEN $2 AND $3 AND longitude BETWEEN $4 AND $5
CREATE INDEX idx_places_geo
    ON places (user_id, latitude, longitude)
    WHERE deleted_at IS NULL;

-- P-02 키워드 검색: WHERE user_id = $1 AND (name ILIKE $2 OR address ILIKE $2)
-- pg_trgm 확장을 통한 GIN 인덱스로 ILIKE 성능 향상
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_places_name_trgm    ON places USING GIN (name    gin_trgm_ops) WHERE deleted_at IS NULL;
CREATE INDEX idx_places_address_trgm ON places USING GIN (address gin_trgm_ops) WHERE deleted_at IS NULL AND address IS NOT NULL;

-- ST-01 통계 월별 집계: WHERE user_id = $1 AND visited_at BETWEEN $2 AND $3
CREATE INDEX idx_places_user_visited_at
    ON places (user_id, visited_at)
    WHERE deleted_at IS NULL;

-- ── place_category ─────────────────────────────────────────
-- 카테고리별 장소 조회: WHERE category_id = $1
CREATE INDEX idx_place_category_category_id
    ON place_category (category_id);

-- ── place_photos ───────────────────────────────────────────
-- 장소 사진 목록 조회: WHERE place_id = $1 ORDER BY sort_order
CREATE INDEX idx_place_photos_place_id
    ON place_photos (place_id, sort_order);

-- ── place_tags ─────────────────────────────────────────────
-- 태그 검색: WHERE place_id = $1
CREATE INDEX idx_place_tags_place_id
    ON place_tags (place_id);

-- ── refresh_tokens ─────────────────────────────────────────
-- 토큰 검증: WHERE token_hash = $1 AND revoked_at IS NULL AND expires_at > NOW()
-- token_hash는 이미 UNIQUE 인덱스 존재 (V004)
-- 만료/무효화 레코드 정리 Batch: WHERE expires_at < NOW() OR revoked_at IS NOT NULL
CREATE INDEX idx_rt_user_id
    ON refresh_tokens (user_id);
CREATE INDEX idx_rt_cleanup
    ON refresh_tokens (expires_at)
    WHERE revoked_at IS NULL;
