-- =============================================================================
-- V4: users.profile_image_url 컬럼 추가
-- Entity(User)와 DDL 불일치 해소 (profile_image_id FK → URL 직접 저장 방식 병행)
-- =============================================================================
ALTER TABLE users
    ADD COLUMN profile_image_url VARCHAR(2048);

-- 기존 시드 데이터의 profile_image_url을 files.cdn_url로 채움
UPDATE users u
SET profile_image_url = f.cdn_url
FROM files f
WHERE u.profile_image_id = f.id;
