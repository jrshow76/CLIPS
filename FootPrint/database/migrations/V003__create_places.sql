-- ============================================================
-- V003: places, place_category, place_photos, place_tags 테이블 생성
-- ============================================================

-- 장소 테이블
CREATE TABLE places (
    id          BIGSERIAL       NOT NULL,
    user_id     UUID            NOT NULL,
    name        VARCHAR(100)    NOT NULL,
    address     VARCHAR(255),
    latitude    NUMERIC(10, 8)  NOT NULL,
    longitude   NUMERIC(11, 8)  NOT NULL,
    visited_at  DATE            NOT NULL,
    memo        TEXT,
    rating      SMALLINT,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ,

    CONSTRAINT pk_places      PRIMARY KEY (id),
    CONSTRAINT fk_places_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_places_latitude    CHECK (latitude BETWEEN -90.0 AND 90.0),
    CONSTRAINT chk_places_longitude   CHECK (longitude BETWEEN -180.0 AND 180.0),
    CONSTRAINT chk_places_rating      CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    CONSTRAINT chk_places_visited_at  CHECK (visited_at <= CURRENT_DATE),
    CONSTRAINT chk_places_name_length CHECK (char_length(name) BETWEEN 1 AND 100)
);

COMMENT ON TABLE  places            IS '장소 기록 테이블';
COMMENT ON COLUMN places.latitude   IS '위도 (-90.0 ~ 90.0, 소수점 8자리)';
COMMENT ON COLUMN places.longitude  IS '경도 (-180.0 ~ 180.0, 소수점 8자리)';
COMMENT ON COLUMN places.visited_at IS '방문일 (미래 날짜 불가)';
COMMENT ON COLUMN places.rating     IS '평점 (1~5 정수, NULL = 미입력)';
COMMENT ON COLUMN places.deleted_at IS '삭제일시 (NULL = 미삭제, Soft Delete)';

CREATE TRIGGER trg_places_updated_at
    BEFORE UPDATE ON places
    FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

-- 장소-카테고리 매핑 (N:M)
CREATE TABLE place_category (
    place_id    BIGINT  NOT NULL,
    category_id BIGINT  NOT NULL,

    CONSTRAINT pk_place_category       PRIMARY KEY (place_id, category_id),
    CONSTRAINT fk_pc_place    FOREIGN KEY (place_id)    REFERENCES places(id)     ON DELETE CASCADE,
    CONSTRAINT fk_pc_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
);

COMMENT ON TABLE place_category IS '장소-카테고리 N:M 매핑 테이블';

-- 장소 사진 테이블
CREATE TABLE place_photos (
    id             BIGSERIAL    NOT NULL,
    place_id       BIGINT       NOT NULL,
    file_name      VARCHAR(255) NOT NULL,
    original_name  VARCHAR(255) NOT NULL,
    file_url       TEXT         NOT NULL,
    thumbnail_url  TEXT,
    file_size      INTEGER      NOT NULL,
    mime_type      VARCHAR(50)  NOT NULL,
    sort_order     SMALLINT     NOT NULL DEFAULT 1,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_place_photos       PRIMARY KEY (id),
    CONSTRAINT fk_photos_place       FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
    CONSTRAINT chk_photos_sort_order CHECK (sort_order BETWEEN 1 AND 5),
    CONSTRAINT chk_photos_mime_type  CHECK (mime_type IN ('image/jpeg', 'image/png', 'image/webp')),
    CONSTRAINT chk_photos_file_size  CHECK (file_size > 0 AND file_size <= 10485760)
);

COMMENT ON TABLE  place_photos           IS '장소 사진 메타데이터 (실제 파일은 CDN 저장)';
COMMENT ON COLUMN place_photos.file_name IS '서버 재생성 파일명 (UUID 기반, 보안용)';
COMMENT ON COLUMN place_photos.file_size IS '파일 크기 (bytes, 최대 10MB)';

-- 장소 태그 테이블
CREATE TABLE place_tags (
    id          BIGSERIAL    NOT NULL,
    place_id    BIGINT       NOT NULL,
    tag         VARCHAR(20)  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_place_tags         PRIMARY KEY (id),
    CONSTRAINT fk_tags_place         FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
    CONSTRAINT uq_place_tag          UNIQUE (place_id, tag),
    CONSTRAINT chk_tags_tag_length   CHECK (char_length(tag) BETWEEN 1 AND 20)
);

COMMENT ON TABLE place_tags IS '장소 태그 테이블 (장소당 최대 10개, 태그당 최대 20자)';
