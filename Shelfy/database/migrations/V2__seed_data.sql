-- =============================================================================
-- Shelfy - V2: 개발용 시드 데이터 (Seed Data)
-- 작성일: 2026-05-09
-- 작성자: DBA
-- 용도: 개발/QA 환경 전용. 운영 환경 실행 절대 금지.
-- 내용: 사용자 10명, 상품 30개, 구독 플랜 5개 (+ 구독/주문 샘플)
-- =============================================================================

-- 운영 환경 보호: search_path 명시 (dev/qa 스키마 격리 권장)
-- SET search_path = shelfy_dev, public;

BEGIN;

-- =============================================================================
-- 1. files (프로필 이미지, 상품 이미지 사전 등록)
--    실제 CDN 파일은 없으나 메타데이터는 삽입한다.
--    uploader_id는 users 삽입 후 FK 참조이므로 임시로 1로 설정 후 업데이트한다.
--    순환 참조 회피: files 먼저 삽입, users의 profile_image_id는 나중에 UPDATE
-- =============================================================================

-- 프로필 이미지 (10개)
INSERT INTO files (id, uploader_id, file_type, original_name, stored_name, cdn_url, file_size, mime_type, created_at)
VALUES
    -- uploader_id는 임시로 1 설정 (users 삽입 후 self-reference이므로 DEFERRABLE FK 활용)
    (1,  1,  'PROFILE_IMAGE', 'profile_alice.jpg',   'p-uuid-0001.jpg', 'https://cdn.shelfy.io/profiles/p-uuid-0001.jpg',   102400, 'image/jpeg', '2026-01-01 09:00:00+09'),
    (2,  2,  'PROFILE_IMAGE', 'profile_bob.jpg',     'p-uuid-0002.jpg', 'https://cdn.shelfy.io/profiles/p-uuid-0002.jpg',   98304,  'image/jpeg', '2026-01-02 09:00:00+09'),
    (3,  3,  'PROFILE_IMAGE', 'profile_carol.png',   'p-uuid-0003.png', 'https://cdn.shelfy.io/profiles/p-uuid-0003.png',   115200, 'image/png',  '2026-01-03 09:00:00+09'),
    (4,  4,  'PROFILE_IMAGE', 'profile_dave.jpg',    'p-uuid-0004.jpg', 'https://cdn.shelfy.io/profiles/p-uuid-0004.jpg',   87040,  'image/jpeg', '2026-01-04 09:00:00+09'),
    (5,  5,  'PROFILE_IMAGE', 'profile_eve.webp',    'p-uuid-0005.webp','https://cdn.shelfy.io/profiles/p-uuid-0005.webp',  76800,  'image/webp', '2026-01-05 09:00:00+09'),
    (6,  6,  'PROFILE_IMAGE', 'profile_frank.jpg',   'p-uuid-0006.jpg', 'https://cdn.shelfy.io/profiles/p-uuid-0006.jpg',   131072, 'image/jpeg', '2026-01-06 09:00:00+09'),
    (7,  7,  'PROFILE_IMAGE', 'profile_grace.png',   'p-uuid-0007.png', 'https://cdn.shelfy.io/profiles/p-uuid-0007.png',   143360, 'image/png',  '2026-01-07 09:00:00+09'),
    (8,  8,  'PROFILE_IMAGE', 'profile_henry.jpg',   'p-uuid-0008.jpg', 'https://cdn.shelfy.io/profiles/p-uuid-0008.jpg',   92160,  'image/jpeg', '2026-01-08 09:00:00+09'),
    (9,  9,  'PROFILE_IMAGE', 'profile_iris.webp',   'p-uuid-0009.webp','https://cdn.shelfy.io/profiles/p-uuid-0009.webp',  65536,  'image/webp', '2026-01-09 09:00:00+09'),
    (10, 10, 'PROFILE_IMAGE', 'profile_jack.jpg',    'p-uuid-0010.jpg', 'https://cdn.shelfy.io/profiles/p-uuid-0010.jpg',   110592, 'image/jpeg', '2026-01-10 09:00:00+09');

-- 상품 썸네일 이미지 (30개, file id 11~40)
INSERT INTO files (id, uploader_id, file_type, original_name, stored_name, cdn_url, file_size, mime_type, created_at)
VALUES
    (11, 1, 'ITEM_IMAGE', 'item-thumb-01.jpg', 'i-uuid-0011.jpg', 'https://cdn.shelfy.io/items/i-uuid-0011.jpg', 512000, 'image/jpeg', '2026-01-15 10:00:00+09'),
    (12, 1, 'ITEM_IMAGE', 'item-thumb-02.jpg', 'i-uuid-0012.jpg', 'https://cdn.shelfy.io/items/i-uuid-0012.jpg', 487424, 'image/jpeg', '2026-01-20 10:00:00+09'),
    (13, 1, 'ITEM_IMAGE', 'item-thumb-03.png', 'i-uuid-0013.png', 'https://cdn.shelfy.io/items/i-uuid-0013.png', 630784, 'image/png',  '2026-01-25 10:00:00+09'),
    (14, 2, 'ITEM_IMAGE', 'item-thumb-04.jpg', 'i-uuid-0014.jpg', 'https://cdn.shelfy.io/items/i-uuid-0014.jpg', 524288, 'image/jpeg', '2026-01-28 10:00:00+09'),
    (15, 2, 'ITEM_IMAGE', 'item-thumb-05.jpg', 'i-uuid-0015.jpg', 'https://cdn.shelfy.io/items/i-uuid-0015.jpg', 450560, 'image/jpeg', '2026-02-01 10:00:00+09'),
    (16, 3, 'ITEM_IMAGE', 'item-thumb-06.webp','i-uuid-0016.webp','https://cdn.shelfy.io/items/i-uuid-0016.webp', 204800, 'image/webp', '2026-02-03 10:00:00+09'),
    (17, 3, 'ITEM_IMAGE', 'item-thumb-07.jpg', 'i-uuid-0017.jpg', 'https://cdn.shelfy.io/items/i-uuid-0017.jpg', 563200, 'image/jpeg', '2026-02-05 10:00:00+09'),
    (18, 3, 'ITEM_IMAGE', 'item-thumb-08.jpg', 'i-uuid-0018.jpg', 'https://cdn.shelfy.io/items/i-uuid-0018.jpg', 409600, 'image/jpeg', '2026-02-07 10:00:00+09'),
    (19, 4, 'ITEM_IMAGE', 'item-thumb-09.png', 'i-uuid-0019.png', 'https://cdn.shelfy.io/items/i-uuid-0019.png', 716800, 'image/png',  '2026-02-10 10:00:00+09'),
    (20, 4, 'ITEM_IMAGE', 'item-thumb-10.jpg', 'i-uuid-0020.jpg', 'https://cdn.shelfy.io/items/i-uuid-0020.jpg', 491520, 'image/jpeg', '2026-02-12 10:00:00+09'),
    (21, 5, 'ITEM_IMAGE', 'item-thumb-11.webp','i-uuid-0021.webp','https://cdn.shelfy.io/items/i-uuid-0021.webp', 307200, 'image/webp', '2026-02-15 10:00:00+09'),
    (22, 5, 'ITEM_IMAGE', 'item-thumb-12.jpg', 'i-uuid-0022.jpg', 'https://cdn.shelfy.io/items/i-uuid-0022.jpg', 552960, 'image/jpeg', '2026-02-18 10:00:00+09'),
    (23, 5, 'ITEM_IMAGE', 'item-thumb-13.jpg', 'i-uuid-0023.jpg', 'https://cdn.shelfy.io/items/i-uuid-0023.jpg', 471040, 'image/jpeg', '2026-02-20 10:00:00+09'),
    (24, 6, 'ITEM_IMAGE', 'item-thumb-14.png', 'i-uuid-0024.png', 'https://cdn.shelfy.io/items/i-uuid-0024.png', 655360, 'image/png',  '2026-02-22 10:00:00+09'),
    (25, 6, 'ITEM_IMAGE', 'item-thumb-15.jpg', 'i-uuid-0025.jpg', 'https://cdn.shelfy.io/items/i-uuid-0025.jpg', 501760, 'image/jpeg', '2026-02-24 10:00:00+09'),
    (26, 7, 'ITEM_IMAGE', 'item-thumb-16.jpg', 'i-uuid-0026.jpg', 'https://cdn.shelfy.io/items/i-uuid-0026.jpg', 524288, 'image/jpeg', '2026-03-01 10:00:00+09'),
    (27, 7, 'ITEM_IMAGE', 'item-thumb-17.webp','i-uuid-0027.webp','https://cdn.shelfy.io/items/i-uuid-0027.webp', 266240, 'image/webp', '2026-03-03 10:00:00+09'),
    (28, 7, 'ITEM_IMAGE', 'item-thumb-18.jpg', 'i-uuid-0028.jpg', 'https://cdn.shelfy.io/items/i-uuid-0028.jpg', 483328, 'image/jpeg', '2026-03-05 10:00:00+09'),
    (29, 8, 'ITEM_IMAGE', 'item-thumb-19.png', 'i-uuid-0029.png', 'https://cdn.shelfy.io/items/i-uuid-0029.png', 737280, 'image/png',  '2026-03-07 10:00:00+09'),
    (30, 8, 'ITEM_IMAGE', 'item-thumb-20.jpg', 'i-uuid-0030.jpg', 'https://cdn.shelfy.io/items/i-uuid-0030.jpg', 511488, 'image/jpeg', '2026-03-10 10:00:00+09'),
    (31, 8, 'ITEM_IMAGE', 'item-thumb-21.jpg', 'i-uuid-0031.jpg', 'https://cdn.shelfy.io/items/i-uuid-0031.jpg', 466944, 'image/jpeg', '2026-03-12 10:00:00+09'),
    (32, 9, 'ITEM_IMAGE', 'item-thumb-22.webp','i-uuid-0032.webp','https://cdn.shelfy.io/items/i-uuid-0032.webp', 286720, 'image/webp', '2026-03-15 10:00:00+09'),
    (33, 9, 'ITEM_IMAGE', 'item-thumb-23.jpg', 'i-uuid-0033.jpg', 'https://cdn.shelfy.io/items/i-uuid-0033.jpg', 528384, 'image/jpeg', '2026-03-17 10:00:00+09'),
    (34, 9, 'ITEM_IMAGE', 'item-thumb-24.jpg', 'i-uuid-0034.jpg', 'https://cdn.shelfy.io/items/i-uuid-0034.jpg', 475136, 'image/jpeg', '2026-03-19 10:00:00+09'),
    (35, 1, 'ITEM_IMAGE', 'item-thumb-25.png', 'i-uuid-0035.png', 'https://cdn.shelfy.io/items/i-uuid-0035.png', 671744, 'image/png',  '2026-03-22 10:00:00+09'),
    (36, 2, 'ITEM_IMAGE', 'item-thumb-26.jpg', 'i-uuid-0036.jpg', 'https://cdn.shelfy.io/items/i-uuid-0036.jpg', 496640, 'image/jpeg', '2026-03-25 10:00:00+09'),
    (37, 3, 'ITEM_IMAGE', 'item-thumb-27.jpg', 'i-uuid-0037.jpg', 'https://cdn.shelfy.io/items/i-uuid-0037.jpg', 542720, 'image/jpeg', '2026-03-28 10:00:00+09'),
    (38, 4, 'ITEM_IMAGE', 'item-thumb-28.webp','i-uuid-0038.webp','https://cdn.shelfy.io/items/i-uuid-0038.webp', 245760, 'image/webp', '2026-04-01 10:00:00+09'),
    (39, 5, 'ITEM_IMAGE', 'item-thumb-29.jpg', 'i-uuid-0039.jpg', 'https://cdn.shelfy.io/items/i-uuid-0039.jpg', 516096, 'image/jpeg', '2026-04-05 10:00:00+09'),
    (40, 6, 'ITEM_IMAGE', 'item-thumb-30.jpg', 'i-uuid-0040.jpg', 'https://cdn.shelfy.io/items/i-uuid-0040.jpg', 503808, 'image/jpeg', '2026-04-08 10:00:00+09');

-- SEQUENCE 동기화
SELECT setval('files_id_seq', 40, true);

-- =============================================================================
-- 2. users (사용자 10명)
--    비밀번호: 모두 'Password1!' (bcrypt $2a$12$... 해시)
--    실제 bcrypt 해시값으로 대체해야 하나 시드 데이터는 고정 해시 사용
--    user 1~7: 셀러 (상품 보유)
--    user 8~10: 구매자/구독자 전용
-- =============================================================================

INSERT INTO users (
    id, email, password_hash, nickname, bio,
    profile_image_id, email_verified,
    agree_terms, agree_privacy, agree_marketing,
    login_failed_count, locked_until, deleted_at,
    created_at, updated_at
)
VALUES
    -- 셀러 겸 구매자
    (1,  'alice@shelfy.dev',  '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwX.P/k8hbNhm5t0S',
     'alice_design',   '포토샵·일러스트 템플릿 전문 셀러입니다.',
     1, TRUE, TRUE, TRUE, TRUE,  0, NULL, NULL,
     '2026-01-01 09:00:00+09', '2026-01-01 09:00:00+09'),

    (2,  'bob@shelfy.dev',    '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwX.P/k8hbNhm5t0S',
     'bob_coder',      '개발 강의와 코드 템플릿을 공유합니다.',
     2, TRUE, TRUE, TRUE, FALSE, 0, NULL, NULL,
     '2026-01-02 09:00:00+09', '2026-01-02 09:00:00+09'),

    (3,  'carol@shelfy.dev',  '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwX.P/k8hbNhm5t0S',
     'carol_photo',    '풍경 사진 작가. 라이트룸 프리셋도 판매해요.',
     3, TRUE, TRUE, TRUE, TRUE,  0, NULL, NULL,
     '2026-01-03 09:00:00+09', '2026-01-03 09:00:00+09'),

    (4,  'dave@shelfy.dev',   '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwX.P/k8hbNhm5t0S',
     'dave_music',     '인디 뮤지션. 루프팩과 샘플팩을 제작합니다.',
     4, TRUE, TRUE, TRUE, FALSE, 0, NULL, NULL,
     '2026-01-04 09:00:00+09', '2026-01-04 09:00:00+09'),

    (5,  'eve@shelfy.dev',    '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwX.P/k8hbNhm5t0S',
     'eve_ux',         'UX 디자이너. Figma 컴포넌트 키트 전문.',
     5, TRUE, TRUE, TRUE, TRUE,  0, NULL, NULL,
     '2026-01-05 09:00:00+09', '2026-01-05 09:00:00+09'),

    (6,  'frank@shelfy.dev',  '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwX.P/k8hbNhm5t0S',
     'frank_dev',      '풀스택 개발자. SaaS 보일러플레이트 판매.',
     6, TRUE, TRUE, TRUE, FALSE, 0, NULL, NULL,
     '2026-01-06 09:00:00+09', '2026-01-06 09:00:00+09'),

    (7,  'grace@shelfy.dev',  '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwX.P/k8hbNhm5t0S',
     'grace_writer',   '콘텐츠 마케터. 카피라이팅 템플릿 작가.',
     7, TRUE, TRUE, TRUE, TRUE,  0, NULL, NULL,
     '2026-01-07 09:00:00+09', '2026-01-07 09:00:00+09'),

    -- 구매자/구독자 전용
    (8,  'henry@shelfy.dev',  '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwX.P/k8hbNhm5t0S',
     'henry_buyer',    NULL,
     8, TRUE, TRUE, TRUE, FALSE, 0, NULL, NULL,
     '2026-01-08 09:00:00+09', '2026-01-08 09:00:00+09'),

    (9,  'iris@shelfy.dev',   '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwX.P/k8hbNhm5t0S',
     'iris_sub',       '구독으로 콘텐츠를 즐기는 사용자.',
     9, TRUE, TRUE, TRUE, TRUE,  0, NULL, NULL,
     '2026-01-09 09:00:00+09', '2026-01-09 09:00:00+09'),

    -- 이메일 미인증 사용자 (셀러 기능 제한 테스트용)
    (10, 'jack@shelfy.dev',   '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwX.P/k8hbNhm5t0S',
     'jack_unverified', NULL,
     10, FALSE, TRUE, TRUE, FALSE, 0, NULL, NULL,
     '2026-01-10 09:00:00+09', '2026-01-10 09:00:00+09');

SELECT setval('users_id_seq', 10, true);

-- =============================================================================
-- 3. items (상품 30개)
--    seller 1~7이 각각 3~5개씩 등록
--    카테고리: 전 카테고리 골고루 배분
--    search_vector는 트리거로 자동 설정됨
-- =============================================================================

INSERT INTO items (
    id, seller_id, title, description, category, sale_type,
    price, thumbnail_image_id, tags, status, view_count,
    deleted_at, created_at, updated_at
)
VALUES
    -- alice_design (seller_id=1) - TEMPLATE 3개
    (1, 1, '포토샵 PSD 레이아웃 50종 패키지',
     '전문 디자이너가 제작한 포토샵 PSD 레이아웃 50종 패키지입니다. SNS 피드, 배너, 명함 등 다양한 용도로 활용 가능합니다. 각 파일은 레이어가 분리되어 편집이 용이합니다.',
     'TEMPLATE', 'BOTH', 15000, 11,
     ARRAY['포토샵','PSD','레이아웃','디자인','템플릿'],
     'PUBLISHED', 1240,
     NULL, '2026-01-15 10:00:00+09', '2026-01-15 10:00:00+09'),

    (2, 1, '일러스트레이터 아이콘 300개 세트',
     '벡터 기반 아이콘 300개 세트입니다. UI, 프레젠테이션, 인쇄물 모두 활용 가능하며 SVG/AI/EPS 포맷으로 제공합니다. 상업적 이용 가능합니다.',
     'TEMPLATE', 'PURCHASE', 9000, 12,
     ARRAY['일러스트레이터','아이콘','벡터','SVG','UI'],
     'PUBLISHED', 892,
     NULL, '2026-01-20 10:00:00+09', '2026-01-20 10:00:00+09'),

    (3, 1, '브랜드 아이덴티티 키트 (비공개 임시저장)',
     '로고, 명함, 레터헤드 등 브랜드 아이덴티티 전체 패키지입니다. 현재 작업 중이며 곧 공개 예정입니다.',
     'TEMPLATE', 'PURCHASE', 25000, 13,
     ARRAY['브랜드','로고','아이덴티티','명함'],
     'DRAFT', 0,
     NULL, '2026-01-25 10:00:00+09', '2026-01-25 10:00:00+09'),

    -- bob_coder (seller_id=2) - COURSE + SOFTWARE
    (4, 2, 'React + TypeScript 실전 강의 (입문~심화)',
     'React와 TypeScript를 처음부터 실전 프로젝트까지 배울 수 있는 강의입니다. 총 40강, 20시간 분량이며 Q&A 채널을 통해 질문에 답변드립니다.',
     'COURSE', 'BOTH', 49000, 14,
     ARRAY['React','TypeScript','프론트엔드','강의','입문'],
     'PUBLISHED', 3450,
     NULL, '2026-01-28 10:00:00+09', '2026-01-28 10:00:00+09'),

    (5, 2, 'Spring Boot 3.x 마이크로서비스 아키텍처 강의',
     'Spring Boot 3.x 기반의 마이크로서비스 설계와 구현을 다루는 강의입니다. Docker, Kubernetes, 서비스 메시 패턴을 포함합니다.',
     'COURSE', 'SUBSCRIBE', NULL, 15,
     ARRAY['Spring','마이크로서비스','Java','백엔드','강의'],
     'PUBLISHED', 2180,
     NULL, '2026-02-01 10:00:00+09', '2026-02-01 10:00:00+09'),

    (6, 2, 'Next.js SaaS 보일러플레이트',
     'Next.js 14, TypeScript, Tailwind CSS, NextAuth, Prisma, Stripe 연동이 완성된 SaaS 스타터 키트입니다. 인증, 결제, 대시보드 기본 구조가 포함되어 있습니다.',
     'SOFTWARE', 'PURCHASE', 79000, 16,
     ARRAY['Next.js','SaaS','보일러플레이트','TypeScript','Stripe'],
     'PUBLISHED', 1890,
     NULL, '2026-02-03 10:00:00+09', '2026-02-03 10:00:00+09'),

    -- carol_photo (seller_id=3) - PHOTO 4개
    (7, 3, '제주도 풍경 사진 100장 컬렉션',
     '직접 촬영한 제주도 풍경 사진 100장 컬렉션입니다. RAW + JPG 포맷으로 제공되며 상업적 이용 가능합니다. 해상도 6000x4000px 이상.',
     'PHOTO', 'PURCHASE', 19000, 17,
     ARRAY['사진','제주도','풍경','RAW','상업용'],
     'PUBLISHED', 678,
     NULL, '2026-02-05 10:00:00+09', '2026-02-05 10:00:00+09'),

    (8, 3, '라이트룸 프리셋 필름 감성 30종',
     '필름 카메라 감성의 라이트룸 프리셋 30종입니다. 인물, 풍경, 음식 사진 모두 적용 가능하며 모바일/데스크톱 라이트룸 모두 지원합니다.',
     'PHOTO', 'BOTH', 12000, 18,
     ARRAY['라이트룸','프리셋','필름','보정','사진'],
     'PUBLISHED', 1540,
     NULL, '2026-02-07 10:00:00+09', '2026-02-07 10:00:00+09'),

    (9, 3, '카페/음식 감성 사진 50장 + 프리셋',
     '카페와 음식 사진 50장 + 전용 라이트룸 프리셋 5종 번들입니다. SNS 피드용으로 최적화되어 있습니다.',
     'PHOTO', 'PURCHASE', 15000, 19,
     ARRAY['카페','음식','사진','프리셋','SNS'],
     'PUBLISHED', 920,
     NULL, '2026-02-10 10:00:00+09', '2026-02-10 10:00:00+09'),

    (10, 3, '흑백 인물 사진 30장 (구독 전용)',
     '매달 새로운 흑백 인물 사진 30장을 제공하는 구독 서비스입니다. 모델 릴리즈 포함, 상업용 이용 가능합니다.',
     'PHOTO', 'SUBSCRIBE', NULL, 20,
     ARRAY['흑백','인물','사진','구독','상업용'],
     'PUBLISHED', 430,
     NULL, '2026-02-12 10:00:00+09', '2026-02-12 10:00:00+09'),

    -- dave_music (seller_id=4) - MUSIC 4개
    (11, 4, 'Lo-Fi Hip Hop 루프팩 Vol.1 (100 Loops)',
     'Lo-Fi Hip Hop 장르의 루프 100개 패키지입니다. BPM 70-90, 다양한 키로 제공됩니다. WAV + MIDI 포맷, 로열티 프리.',
     'MUSIC', 'PURCHASE', 22000, 21,
     ARRAY['LoFi','힙합','루프','샘플','WAV'],
     'PUBLISHED', 2340,
     NULL, '2026-02-15 10:00:00+09', '2026-02-15 10:00:00+09'),

    (12, 4, 'Cinematic Orchestra 사운드킷',
     '영상 BGM에 최적화된 오케스트라 사운드킷입니다. 스트링, 브라스, 퍼커션 등 200개 이상의 샘플이 포함되어 있습니다.',
     'MUSIC', 'BOTH', 35000, 22,
     ARRAY['시네마틱','오케스트라','영상BGM','사운드킷','로열티프리'],
     'PUBLISHED', 1120,
     NULL, '2026-02-18 10:00:00+09', '2026-02-18 10:00:00+09'),

    (13, 4, '매월 새 루프팩 구독 서비스',
     '매달 새로운 장르의 루프팩을 구독으로 제공합니다. 월간 50+개 루프, 분기 200+개, 연간 구독 시 아카이브 전체 접근 가능.',
     'MUSIC', 'SUBSCRIBE', NULL, 23,
     ARRAY['루프팩','구독','샘플팩','프로듀서','월간'],
     'PUBLISHED', 560,
     NULL, '2026-02-20 10:00:00+09', '2026-02-20 10:00:00+09'),

    (14, 4, 'K-Pop 보컬 초퍼 샘플팩',
     'K-Pop 스타일 보컬 초퍼 샘플팩입니다. 다양한 피치와 이펙트가 적용된 100개 샘플 포함.',
     'MUSIC', 'PURCHASE', 18000, 24,
     ARRAY['K-Pop','보컬','초퍼','샘플','힙합'],
     'PUBLISHED', 870,
     NULL, '2026-02-22 10:00:00+09', '2026-02-22 10:00:00+09'),

    -- eve_ux (seller_id=5) - TEMPLATE (Figma) 4개
    (15, 5, 'Figma Design System 컴포넌트 키트',
     '프로덕션 레벨의 Figma 디자인 시스템 컴포넌트 키트입니다. 500개 이상의 컴포넌트, 다크/라이트 모드, Auto Layout 적용.',
     'TEMPLATE', 'BOTH', 39000, 25,
     ARRAY['Figma','디자인시스템','컴포넌트','UI킷','다크모드'],
     'PUBLISHED', 4120,
     NULL, '2026-02-24 10:00:00+09', '2026-02-24 10:00:00+09'),

    (16, 5, 'Figma 대시보드 UI 키트',
     'SaaS, 어드민, 분석 대시보드에 최적화된 Figma UI 키트입니다. 차트, 테이블, 폼 컴포넌트 포함.',
     'TEMPLATE', 'PURCHASE', 25000, 26,
     ARRAY['Figma','대시보드','SaaS','어드민','UI킷'],
     'PUBLISHED', 2670,
     NULL, '2026-03-01 10:00:00+09', '2026-03-01 10:00:00+09'),

    (17, 5, 'Figma 프레젠테이션 템플릿 20종',
     '세련된 프레젠테이션 Figma 템플릿 20종입니다. 비즈니스, 스타트업 피치덱, 포트폴리오 등 다양한 목적에 적합합니다.',
     'TEMPLATE', 'PURCHASE', 12000, 27,
     ARRAY['Figma','프레젠테이션','피치덱','포트폴리오','템플릿'],
     'PUBLISHED', 1450,
     NULL, '2026-03-03 10:00:00+09', '2026-03-03 10:00:00+09'),

    (18, 5, 'UX 리서치 템플릿 패키지',
     '사용자 인터뷰, 설문, 어피니티 다이어그램, 페르소나 등 UX 리서치에 필요한 Figma 템플릿 모음입니다.',
     'TEMPLATE', 'BOTH', 18000, 28,
     ARRAY['UX리서치','페르소나','인터뷰','Figma','디자인씽킹'],
     'PUBLISHED', 980,
     NULL, '2026-03-05 10:00:00+09', '2026-03-05 10:00:00+09'),

    -- frank_dev (seller_id=6) - SOFTWARE 4개
    (19, 6, 'Django REST API 보일러플레이트',
     'Django + DRF + JWT + PostgreSQL + Docker로 구성된 REST API 보일러플레이트입니다. 인증, RBAC, Celery 비동기 처리 포함.',
     'SOFTWARE', 'PURCHASE', 45000, 29,
     ARRAY['Django','Python','REST API','보일러플레이트','Docker'],
     'PUBLISHED', 1230,
     NULL, '2026-03-07 10:00:00+09', '2026-03-07 10:00:00+09'),

    (20, 6, 'React Native 앱 스타터킷',
     'React Native + Expo + TypeScript로 구성된 앱 스타터킷입니다. 인증, 푸시 알림, 결제(Stripe), 다국어 지원 포함.',
     'SOFTWARE', 'PURCHASE', 65000, 30,
     ARRAY['React Native','Expo','TypeScript','모바일','앱'],
     'PUBLISHED', 1780,
     NULL, '2026-03-10 10:00:00+09', '2026-03-10 10:00:00+09'),

    (21, 6, 'GitHub Actions CI/CD 템플릿 컬렉션',
     '다양한 언어와 플랫폼에 대한 GitHub Actions 워크플로 템플릿 20종입니다. Node.js, Python, Java, Docker, AWS 배포 포함.',
     'SOFTWARE', 'PURCHASE', 12000, 31,
     ARRAY['GitHub Actions','CI/CD','DevOps','워크플로','자동화'],
     'PUBLISHED', 2450,
     NULL, '2026-03-12 10:00:00+09', '2026-03-12 10:00:00+09'),

    (22, 6, '월간 코드 스니펫 구독 서비스',
     '매달 실무에서 바로 쓸 수 있는 코드 스니펫 50+개를 구독으로 제공합니다. JavaScript, Python, Shell 등 다양한 언어 포함.',
     'SOFTWARE', 'SUBSCRIBE', NULL, 32,
     ARRAY['코드스니펫','구독','JavaScript','Python','생산성'],
     'PUBLISHED', 340,
     NULL, '2026-03-15 10:00:00+09', '2026-03-15 10:00:00+09'),

    -- grace_writer (seller_id=7) - DIGITAL_CONTENT 4개
    (23, 7, '마케팅 카피라이팅 100 템플릿',
     '제품 소개, 광고 카피, 이메일 뉴스레터, SNS 게시글 등 마케팅 전반에 활용 가능한 카피라이팅 템플릿 100종입니다.',
     'DIGITAL_CONTENT', 'PURCHASE', 19000, 33,
     ARRAY['카피라이팅','마케팅','템플릿','SNS','광고'],
     'PUBLISHED', 1670,
     NULL, '2026-03-17 10:00:00+09', '2026-03-17 10:00:00+09'),

    (24, 7, 'B2B 이메일 세일즈 스크립트 50종',
     'B2B 영업 이메일에 특화된 세일즈 스크립트 50종입니다. 첫 접촉, 팔로업, 클로징 등 단계별 템플릿을 제공합니다.',
     'DIGITAL_CONTENT', 'PURCHASE', 25000, 34,
     ARRAY['B2B','이메일','세일즈','영업','비즈니스'],
     'PUBLISHED', 890,
     NULL, '2026-03-19 10:00:00+09', '2026-03-19 10:00:00+09'),

    (25, 7, '월간 콘텐츠 마케팅 플래너 구독',
     '매달 SNS 콘텐츠 캘린더, 해시태그 전략, 트렌드 키워드 분석 보고서를 구독으로 제공합니다.',
     'DIGITAL_CONTENT', 'SUBSCRIBE', NULL, 35,
     ARRAY['콘텐츠마케팅','SNS','플래너','구독','트렌드'],
     'PUBLISHED', 520,
     NULL, '2026-03-22 10:00:00+09', '2026-03-22 10:00:00+09'),

    (26, 7, 'ChatGPT 프롬프트 200선 (마케팅 특화)',
     '마케팅 업무에 특화된 ChatGPT 프롬프트 200개를 카테고리별로 정리한 가이드북입니다. PDF + Notion 템플릿 제공.',
     'DIGITAL_CONTENT', 'BOTH', 13000, 36,
     ARRAY['ChatGPT','프롬프트','AI','마케팅','생산성'],
     'PUBLISHED', 2890,
     NULL, '2026-03-25 10:00:00+09', '2026-03-25 10:00:00+09'),

    -- 추가 상품 (seller 1~6이 각 1개씩 추가 - 총 30개 맞추기)
    (27, 1, 'Notion 업무 관리 올인원 템플릿',
     '프로젝트 관리, 일정 추적, 독서 기록, 습관 트래커까지 업무와 개인 생산성 모두를 관리할 수 있는 Notion 템플릿입니다.',
     'TEMPLATE', 'PURCHASE', 7900, 37,
     ARRAY['Notion','생산성','업무관리','템플릿','프로젝트'],
     'PUBLISHED', 3210,
     NULL, '2026-03-28 10:00:00+09', '2026-03-28 10:00:00+09'),

    (28, 2, 'PostgreSQL 쿼리 최적화 가이드',
     'EXPLAIN ANALYZE 분석, 인덱스 설계, 파티셔닝, Vacuum 튜닝 등 PostgreSQL 성능 최적화의 모든 것을 담은 전자책입니다.',
     'DIGITAL_CONTENT', 'PURCHASE', 22000, 38,
     ARRAY['PostgreSQL','쿼리최적화','DBA','데이터베이스','전자책'],
     'PUBLISHED', 1560,
     NULL, '2026-04-01 10:00:00+09', '2026-04-01 10:00:00+09'),

    (29, 3, '웨딩 사진 라이트룸 프리셋 15종',
     '웨딩 사진 전문 라이트룸 프리셋 15종입니다. 맑은 화이트 톤, 빈티지 필름, 무드 있는 다크 톤 스타일을 포함합니다.',
     'PHOTO', 'PURCHASE', 14000, 39,
     ARRAY['웨딩','라이트룸','프리셋','사진','보정'],
     'PUBLISHED', 730,
     NULL, '2026-04-05 10:00:00+09', '2026-04-05 10:00:00+09'),

    (30, 4, 'Trap & Drill 비트메이킹 루프팩',
     'Trap과 Drill 장르에 최적화된 드럼 루프, 멜로디 루프, FX 샘플 150개 패키지입니다. 상업적 이용 가능.',
     'MUSIC', 'PURCHASE', 28000, 40,
     ARRAY['Trap','Drill','비트','루프','드럼'],
     'PUBLISHED', 1890,
     NULL, '2026-04-08 10:00:00+09', '2026-04-08 10:00:00+09');

SELECT setval('items_id_seq', 30, true);

-- =============================================================================
-- 4. item_images (각 상품별 대표 이미지 연결)
-- =============================================================================

INSERT INTO item_images (id, item_id, file_id, sort_order, is_thumbnail, created_at)
VALUES
    (1,  1,  11, 0, TRUE,  '2026-01-15 10:00:00+09'),
    (2,  2,  12, 0, TRUE,  '2026-01-20 10:00:00+09'),
    (3,  3,  13, 0, TRUE,  '2026-01-25 10:00:00+09'),
    (4,  4,  14, 0, TRUE,  '2026-01-28 10:00:00+09'),
    (5,  5,  15, 0, TRUE,  '2026-02-01 10:00:00+09'),
    (6,  6,  16, 0, TRUE,  '2026-02-03 10:00:00+09'),
    (7,  7,  17, 0, TRUE,  '2026-02-05 10:00:00+09'),
    (8,  8,  18, 0, TRUE,  '2026-02-07 10:00:00+09'),
    (9,  9,  19, 0, TRUE,  '2026-02-10 10:00:00+09'),
    (10, 10, 20, 0, TRUE,  '2026-02-12 10:00:00+09'),
    (11, 11, 21, 0, TRUE,  '2026-02-15 10:00:00+09'),
    (12, 12, 22, 0, TRUE,  '2026-02-18 10:00:00+09'),
    (13, 13, 23, 0, TRUE,  '2026-02-20 10:00:00+09'),
    (14, 14, 24, 0, TRUE,  '2026-02-22 10:00:00+09'),
    (15, 15, 25, 0, TRUE,  '2026-02-24 10:00:00+09'),
    (16, 16, 26, 0, TRUE,  '2026-03-01 10:00:00+09'),
    (17, 17, 27, 0, TRUE,  '2026-03-03 10:00:00+09'),
    (18, 18, 28, 0, TRUE,  '2026-03-05 10:00:00+09'),
    (19, 19, 29, 0, TRUE,  '2026-03-07 10:00:00+09'),
    (20, 20, 30, 0, TRUE,  '2026-03-10 10:00:00+09'),
    (21, 21, 31, 0, TRUE,  '2026-03-12 10:00:00+09'),
    (22, 22, 32, 0, TRUE,  '2026-03-15 10:00:00+09'),
    (23, 23, 33, 0, TRUE,  '2026-03-17 10:00:00+09'),
    (24, 24, 34, 0, TRUE,  '2026-03-19 10:00:00+09'),
    (25, 25, 35, 0, TRUE,  '2026-03-22 10:00:00+09'),
    (26, 26, 36, 0, TRUE,  '2026-03-25 10:00:00+09'),
    (27, 27, 37, 0, TRUE,  '2026-03-28 10:00:00+09'),
    (28, 28, 38, 0, TRUE,  '2026-04-01 10:00:00+09'),
    (29, 29, 39, 0, TRUE,  '2026-04-05 10:00:00+09'),
    (30, 30, 40, 0, TRUE,  '2026-04-08 10:00:00+09');

SELECT setval('item_images_id_seq', 30, true);

-- items.thumbnail_image_id 업데이트 (파일 FK 설정)
UPDATE items SET thumbnail_image_id = 11 WHERE id = 1;
UPDATE items SET thumbnail_image_id = 12 WHERE id = 2;
UPDATE items SET thumbnail_image_id = 13 WHERE id = 3;
UPDATE items SET thumbnail_image_id = 14 WHERE id = 4;
UPDATE items SET thumbnail_image_id = 15 WHERE id = 5;
UPDATE items SET thumbnail_image_id = 16 WHERE id = 6;
UPDATE items SET thumbnail_image_id = 17 WHERE id = 7;
UPDATE items SET thumbnail_image_id = 18 WHERE id = 8;
UPDATE items SET thumbnail_image_id = 19 WHERE id = 9;
UPDATE items SET thumbnail_image_id = 20 WHERE id = 10;
UPDATE items SET thumbnail_image_id = 21 WHERE id = 11;
UPDATE items SET thumbnail_image_id = 22 WHERE id = 12;
UPDATE items SET thumbnail_image_id = 23 WHERE id = 13;
UPDATE items SET thumbnail_image_id = 24 WHERE id = 14;
UPDATE items SET thumbnail_image_id = 25 WHERE id = 15;
UPDATE items SET thumbnail_image_id = 26 WHERE id = 16;
UPDATE items SET thumbnail_image_id = 27 WHERE id = 17;
UPDATE items SET thumbnail_image_id = 28 WHERE id = 18;
UPDATE items SET thumbnail_image_id = 29 WHERE id = 19;
UPDATE items SET thumbnail_image_id = 30 WHERE id = 20;
UPDATE items SET thumbnail_image_id = 31 WHERE id = 21;
UPDATE items SET thumbnail_image_id = 32 WHERE id = 22;
UPDATE items SET thumbnail_image_id = 33 WHERE id = 23;
UPDATE items SET thumbnail_image_id = 34 WHERE id = 24;
UPDATE items SET thumbnail_image_id = 35 WHERE id = 25;
UPDATE items SET thumbnail_image_id = 36 WHERE id = 26;
UPDATE items SET thumbnail_image_id = 37 WHERE id = 27;
UPDATE items SET thumbnail_image_id = 38 WHERE id = 28;
UPDATE items SET thumbnail_image_id = 39 WHERE id = 29;
UPDATE items SET thumbnail_image_id = 40 WHERE id = 30;

-- =============================================================================
-- 5. subscription_plans (구독 플랜 5개 - 요청 사양)
--    SUBSCRIBE 또는 BOTH 타입 상품에만 플랜 연결
--    item 1 (BOTH): Basic 플랜
--    item 4 (BOTH): Basic, Premium 플랜
--    item 5 (SUBSCRIBE): Standard 플랜
--    item 13 (SUBSCRIBE): Monthly, Quarterly 플랜
--    총 5개 플랜
-- =============================================================================

INSERT INTO subscription_plans (
    id, item_id, plan_name, period, plan_price, description,
    is_active, created_at, updated_at
)
VALUES
    -- item 1: 포토샵 PSD 레이아웃 50종 (BOTH) - Basic 월간
    (1, 1,  'Basic',    'MONTHLY',   4900,
     '매월 새로운 PSD 레이아웃 5종 + 기존 라이브러리 접근권',
     TRUE, '2026-01-15 10:00:00+09', '2026-01-15 10:00:00+09'),

    -- item 4: React + TypeScript 강의 (BOTH) - Basic/Premium
    (2, 4,  'Basic',    'MONTHLY',   9900,
     '강의 영상 무제한 시청 + 커뮤니티 Q&A 접근',
     TRUE, '2026-01-28 10:00:00+09', '2026-01-28 10:00:00+09'),

    (3, 4,  'Premium',  'YEARLY',    89000,
     '강의 영상 + 소스코드 전체 다운로드 + 1:1 코드 리뷰 2회/월 (연간, 2개월 무료)',
     TRUE, '2026-01-28 10:00:00+09', '2026-01-28 10:00:00+09'),

    -- item 5: Spring Boot 마이크로서비스 강의 (SUBSCRIBE 전용) - Standard
    (4, 5,  'Standard', 'MONTHLY',   19900,
     '강의 영상 무제한 시청 + 월간 업데이트 콘텐츠 + Discord 멘토링 채널',
     TRUE, '2026-02-01 10:00:00+09', '2026-02-01 10:00:00+09'),

    -- item 13: 매월 새 루프팩 구독 서비스 (SUBSCRIBE 전용) - Monthly/Quarterly
    (5, 13, 'Monthly',  'MONTHLY',   14900,
     '매달 50개 이상 루프팩 신규 업로드 + 전월 아카이브 접근',
     TRUE, '2026-02-20 10:00:00+09', '2026-02-20 10:00:00+09');

SELECT setval('subscription_plans_id_seq', 5, true);

-- =============================================================================
-- 6. subscriptions (구독 샘플)
--    henry(8), iris(9)가 구독자로 참여
-- =============================================================================

INSERT INTO subscriptions (
    id, subscriber_id, item_id, plan_id,
    plan_name, amount, payment_method, status,
    started_at, next_billing_at,
    cancelled_at, active_until,
    created_at, updated_at
)
VALUES
    -- henry(8)가 item 4의 Basic 플랜 구독 (ACTIVE)
    (1, 8, 4, 2,
     'Basic', 9900, 'CARD', 'ACTIVE',
     '2026-04-01 10:00:00+09', '2026-05-01 10:00:00+09',
     NULL, NULL,
     '2026-04-01 10:00:00+09', '2026-04-01 10:00:00+09'),

    -- henry(8)가 item 5의 Standard 플랜 구독 (ACTIVE)
    (2, 8, 5, 4,
     'Standard', 19900, 'CARD', 'ACTIVE',
     '2026-03-10 10:00:00+09', '2026-05-10 10:00:00+09',
     NULL, NULL,
     '2026-03-10 10:00:00+09', '2026-04-10 10:00:00+09'),

    -- iris(9)가 item 1의 Basic 플랜 구독 (ACTIVE)
    (3, 9, 1, 1,
     'Basic', 4900, 'CARD', 'ACTIVE',
     '2026-04-15 10:00:00+09', '2026-05-15 10:00:00+09',
     NULL, NULL,
     '2026-04-15 10:00:00+09', '2026-04-15 10:00:00+09'),

    -- iris(9)가 item 13의 Monthly 플랜 구독 (CANCEL_REQUESTED)
    (4, 9, 13, 5,
     'Monthly', 14900, 'CARD', 'CANCEL_REQUESTED',
     '2026-03-01 10:00:00+09', '2026-05-01 10:00:00+09',
     '2026-04-25 10:00:00+09', '2026-05-01 09:59:59+09',
     '2026-03-01 10:00:00+09', '2026-04-25 10:00:00+09'),

    -- alice(1)가 item 4의 Premium 플랜 구독 (CANCELLED - 해지 완료)
    (5, 1, 4, 3,
     'Premium', 89000, 'CARD', 'CANCELLED',
     '2026-02-01 10:00:00+09', '2026-03-01 10:00:00+09',
     '2026-02-15 10:00:00+09', '2026-02-28 23:59:59+09',
     '2026-02-01 10:00:00+09', '2026-03-01 10:00:00+09');

SELECT setval('subscriptions_id_seq', 5, true);

-- =============================================================================
-- 7. subscription_payments (구독 결제 이력)
-- =============================================================================

INSERT INTO subscription_payments (
    id, subscription_id, amount, pg_transaction_id,
    status, billing_at, paid_at, failed_reason, created_at
)
VALUES
    -- subscription 1 (henry - item 4 Basic): 1회차 성공
    (1, 1, 9900, 'PG-TXN-00001-20260401',
     'SUCCESS', '2026-04-01 10:00:00+09', '2026-04-01 10:01:23+09',
     NULL, '2026-04-01 10:00:00+09'),

    -- subscription 2 (henry - item 5 Standard): 3월, 4월 성공
    (2, 2, 19900, 'PG-TXN-00002-20260310',
     'SUCCESS', '2026-03-10 10:00:00+09', '2026-03-10 10:02:05+09',
     NULL, '2026-03-10 10:00:00+09'),

    (3, 2, 19900, 'PG-TXN-00003-20260410',
     'SUCCESS', '2026-04-10 10:00:00+09', '2026-04-10 10:01:44+09',
     NULL, '2026-04-10 10:00:00+09'),

    -- subscription 3 (iris - item 1 Basic): 1회차 성공
    (4, 3, 4900, 'PG-TXN-00004-20260415',
     'SUCCESS', '2026-04-15 10:00:00+09', '2026-04-15 10:01:12+09',
     NULL, '2026-04-15 10:00:00+09'),

    -- subscription 4 (iris - item 13 Monthly): 3월 성공, 4월 실패
    (5, 4, 14900, 'PG-TXN-00005-20260301',
     'SUCCESS', '2026-03-01 10:00:00+09', '2026-03-01 10:01:55+09',
     NULL, '2026-03-01 10:00:00+09'),

    (6, 4, 14900, NULL,
     'FAILED', '2026-04-01 10:00:00+09', NULL,
     '카드 한도 초과', '2026-04-01 10:00:00+09'),

    -- subscription 5 (alice - item 4 Premium): 2월 성공
    (7, 5, 89000, 'PG-TXN-00006-20260201',
     'SUCCESS', '2026-02-01 10:00:00+09', '2026-02-01 10:02:33+09',
     NULL, '2026-02-01 10:00:00+09');

SELECT setval('subscription_payments_id_seq', 7, true);

-- =============================================================================
-- 8. orders (구매 주문 샘플)
-- =============================================================================

INSERT INTO orders (
    id, buyer_id, item_id, item_title,
    amount, payment_method, pg_transaction_id,
    status, refund_reason, refunded_at, paid_at,
    created_at, updated_at
)
VALUES
    -- henry(8) 구매: item 2 (아이콘 세트)
    (1, 8, 2, '일러스트레이터 아이콘 300개 세트',
     9000, 'CARD', 'PG-ORD-00001-20260210',
     'COMPLETED', NULL, NULL, '2026-02-10 11:00:00+09',
     '2026-02-10 11:00:00+09', '2026-02-10 11:00:00+09'),

    -- henry(8) 구매: item 11 (Lo-Fi 루프팩)
    (2, 8, 11, 'Lo-Fi Hip Hop 루프팩 Vol.1 (100 Loops)',
     22000, 'KAKAO_PAY', 'PG-ORD-00002-20260301',
     'COMPLETED', NULL, NULL, '2026-03-01 14:00:00+09',
     '2026-03-01 14:00:00+09', '2026-03-01 14:00:00+09'),

    -- henry(8) 구매: item 27 (Notion 템플릿)
    (3, 8, 27, 'Notion 업무 관리 올인원 템플릿',
     7900, 'CARD', 'PG-ORD-00003-20260320',
     'COMPLETED', NULL, NULL, '2026-03-20 09:30:00+09',
     '2026-03-20 09:30:00+09', '2026-03-20 09:30:00+09'),

    -- iris(9) 구매: item 6 (Next.js 보일러플레이트)
    (4, 9, 6, 'Next.js SaaS 보일러플레이트',
     79000, 'CARD', 'PG-ORD-00004-20260315',
     'COMPLETED', NULL, NULL, '2026-03-15 16:00:00+09',
     '2026-03-15 16:00:00+09', '2026-03-15 16:00:00+09'),

    -- iris(9) 구매: item 23 (카피라이팅 템플릿) - 환불됨
    (5, 9, 23, '마케팅 카피라이팅 100 템플릿',
     19000, 'NAVER_PAY', 'PG-ORD-00005-20260401',
     'REFUNDED', '단순 변심', '2026-04-05 10:00:00+09', '2026-04-01 13:00:00+09',
     '2026-04-01 13:00:00+09', '2026-04-05 10:00:00+09'),

    -- alice(1) 구매: item 20 (React Native 앱 스타터킷)
    (6, 1, 20, 'React Native 앱 스타터킷',
     65000, 'CARD', 'PG-ORD-00006-20260220',
     'COMPLETED', NULL, NULL, '2026-02-20 15:00:00+09',
     '2026-02-20 15:00:00+09', '2026-02-20 15:00:00+09'),

    -- alice(1) 구매: item 26 (ChatGPT 프롬프트)
    (7, 1, 26, 'ChatGPT 프롬프트 200선 (마케팅 특화)',
     13000, 'KAKAO_PAY', 'PG-ORD-00007-20260410',
     'COMPLETED', NULL, NULL, '2026-04-10 11:30:00+09',
     '2026-04-10 11:30:00+09', '2026-04-10 11:30:00+09'),

    -- bob(2) 구매: item 15 (Figma 디자인 시스템)
    (8, 2, 15, 'Figma Design System 컴포넌트 키트',
     39000, 'CARD', 'PG-ORD-00008-20260310',
     'COMPLETED', NULL, NULL, '2026-03-10 10:00:00+09',
     '2026-03-10 10:00:00+09', '2026-03-10 10:00:00+09'),

    -- bob(2) 구매: item 7 (제주도 사진)
    (9, 2, 7, '제주도 풍경 사진 100장 컬렉션',
     19000, 'CARD', 'PG-ORD-00009-20260405',
     'COMPLETED', NULL, NULL, '2026-04-05 09:00:00+09',
     '2026-04-05 09:00:00+09', '2026-04-05 09:00:00+09'),

    -- dave(4) 구매: item 28 (PostgreSQL 가이드)
    (10, 4, 28, 'PostgreSQL 쿼리 최적화 가이드',
     22000, 'CARD', 'PG-ORD-00010-20260420',
     'COMPLETED', NULL, NULL, '2026-04-20 14:00:00+09',
     '2026-04-20 14:00:00+09', '2026-04-20 14:00:00+09');

SELECT setval('orders_id_seq', 10, true);

-- =============================================================================
-- 9. email_verifications (미인증 사용자 jack용 토큰)
-- =============================================================================

INSERT INTO email_verifications (
    id, user_id, token, expires_at, verified_at, created_at
)
VALUES
    -- jack(10)의 미인증 토큰
    (1, 10,
     'ev-token-jack-2026-0110-unverified-uuid-placeholder',
     '2026-05-10 09:00:00+09',
     NULL,
     '2026-05-09 09:00:00+09');

SELECT setval('email_verifications_id_seq', 1, true);

-- =============================================================================
-- 10. refresh_tokens (개발 테스트용 샘플 토큰)
-- =============================================================================

INSERT INTO refresh_tokens (
    id, user_id, token_hash, expires_at, revoked_at, created_at
)
VALUES
    -- alice(1) 유효 토큰
    (1, 1,
     'sha256-hash-placeholder-alice-refresh-token-000001',
     '2026-05-23 09:00:00+09',
     NULL,
     '2026-05-09 09:00:00+09'),

    -- henry(8) 유효 토큰
    (2, 8,
     'sha256-hash-placeholder-henry-refresh-token-000002',
     '2026-05-23 09:00:00+09',
     NULL,
     '2026-05-09 09:00:00+09'),

    -- iris(9) 만료 토큰 (revoked)
    (3, 9,
     'sha256-hash-placeholder-iris-refresh-token-revoked',
     '2026-04-23 09:00:00+09',
     '2026-04-20 10:00:00+09',
     '2026-04-09 09:00:00+09');

SELECT setval('refresh_tokens_id_seq', 3, true);

COMMIT;

-- =============================================================================
-- 검증 쿼리 (삽입 후 확인용 - 운영 환경에서는 실행 금지)
-- =============================================================================
/*
-- 사용자 수 확인
SELECT COUNT(*) AS user_count FROM users;                    -- 기대: 10

-- 상품 수 확인 (상태별)
SELECT status, COUNT(*) AS cnt FROM items GROUP BY status;   -- PUBLISHED: 29, DRAFT: 1

-- 구독 플랜 수 확인
SELECT COUNT(*) AS plan_count FROM subscription_plans;       -- 기대: 5

-- 활성 구독 확인
SELECT s.id, u.nickname, i.title, sp.plan_name, s.status
FROM subscriptions s
JOIN users u ON u.id = s.subscriber_id
JOIN items i ON i.id = s.item_id
JOIN subscription_plans sp ON sp.id = s.plan_id
ORDER BY s.id;

-- 전문 검색 벡터 확인 (트리거 동작 검증)
SELECT id, title, search_vector IS NOT NULL AS has_vector
FROM items LIMIT 5;

-- 전문 검색 테스트
SELECT id, title FROM items
WHERE search_vector @@ to_tsquery('simple', '포토샵')
ORDER BY ts_rank(search_vector, to_tsquery('simple', '포토샵')) DESC;
*/
