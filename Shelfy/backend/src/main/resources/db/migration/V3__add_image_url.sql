-- =============================================================================
-- V3: item_images.image_url 컬럼 추가
-- Entity(ItemImage)와 DDL 불일치 해소
-- =============================================================================
ALTER TABLE item_images
    ADD COLUMN image_url VARCHAR(2048) NOT NULL DEFAULT '';

-- 기존 시드 데이터의 image_url을 files.cdn_url로 채움
UPDATE item_images ii
SET image_url = f.cdn_url
FROM files f
WHERE ii.file_id = f.id;
