-- ============================================================
-- V002: categories 테이블 생성 + 기본 카테고리 데이터 삽입
-- 시스템 기본 카테고리(user_id=NULL)와 사용자 정의 카테고리를 동일 테이블 관리
-- ============================================================

CREATE TABLE categories (
    id          BIGSERIAL    NOT NULL,
    user_id     UUID,
    name        VARCHAR(20)  NOT NULL,
    color       VARCHAR(7)   NOT NULL DEFAULT '#94A3B8',
    icon        VARCHAR(50)  NOT NULL DEFAULT 'default',
    is_default  BOOLEAN      NOT NULL DEFAULT FALSE,
    sort_order  INTEGER      NOT NULL DEFAULT 999,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_categories      PRIMARY KEY (id),
    CONSTRAINT fk_categories_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_categories_color CHECK (color ~ '^#[0-9A-Fa-f]{6}$')
);

COMMENT ON TABLE  categories            IS '카테고리 테이블 (시스템 기본 + 사용자 정의 통합)';
COMMENT ON COLUMN categories.user_id   IS 'NULL = 시스템 기본 카테고리, 값 있음 = 사용자 정의 카테고리';
COMMENT ON COLUMN categories.is_default IS 'TRUE = 시스템 기본 카테고리 (수정/삭제 불가)';
COMMENT ON COLUMN categories.sort_order IS '목록 정렬 순서';

CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

-- 기본 카테고리 8개 삽입
INSERT INTO categories (user_id, name, color, icon, is_default, sort_order) VALUES
    (NULL, '맛집',   '#EF4444', 'restaurant',  TRUE, 1),
    (NULL, '카페',   '#F59E0B', 'cafe',         TRUE, 2),
    (NULL, '관광지', '#10B981', 'landmark',     TRUE, 3),
    (NULL, '숙소',   '#3B82F6', 'hotel',        TRUE, 4),
    (NULL, '쇼핑',   '#8B5CF6', 'shopping',     TRUE, 5),
    (NULL, '자연',   '#22C55E', 'nature',       TRUE, 6),
    (NULL, '문화',   '#EC4899', 'culture',      TRUE, 7),
    (NULL, '기타',   '#94A3B8', 'default',      TRUE, 8);
