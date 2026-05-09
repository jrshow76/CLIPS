-- ============================================================
-- 시드 데이터 (테스트 / 개발 환경용)
-- 운영 환경에는 절대 실행하지 않는다.
-- ============================================================

-- 테스트 사용자 2명 (비밀번호: Test1234! → bcrypt 해시)
INSERT INTO users (id, email, password_hash, nickname) VALUES
    ('00000000-0000-0000-0000-000000000001', 'test1@footprint.dev',
     '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', '여행자김씨'),
    ('00000000-0000-0000-0000-000000000002', 'test2@footprint.dev',
     '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', '탐험가이씨');

-- 샘플 장소 10건 (test1 사용자)
INSERT INTO places (user_id, name, address, latitude, longitude, visited_at, memo, rating) VALUES
    ('00000000-0000-0000-0000-000000000001', '경복궁',       '서울 종로구 사직로 161',        37.57952, 126.97706, '2026-03-15', '봄 벚꽃 시즌에 방문. 광화문 주변이 정말 아름다웠다.', 5),
    ('00000000-0000-0000-0000-000000000001', '남산타워',      '서울 용산구 남산공원길 105',    37.55139, 126.98824, '2026-03-20', '야경이 환상적. 커플 자물쇠 거는 곳도 있음.',          4),
    ('00000000-0000-0000-0000-000000000001', '북촌한옥마을',  '서울 종로구 계동길 37',         37.58275, 126.98372, '2026-03-21', '골목길이 예쁘다. 오전 일찍 가야 조용히 볼 수 있음.',  4),
    ('00000000-0000-0000-0000-000000000001', '광장시장',      '서울 종로구 창경궁로 88',       37.57008, 126.99934, '2026-04-01', '육회비빔밥과 빈대떡 강추! 마약김밥도 맛있음.',        5),
    ('00000000-0000-0000-0000-000000000001', '성수동 카페거리','서울 성동구 서울숲2길',         37.54477, 127.05601, '2026-04-10', '힙한 카페들이 많다. 주말은 웨이팅 필수.',             3),
    ('00000000-0000-0000-0000-000000000001', '제주 한라산',   '제주 서귀포시 토평동 산15-1',   33.36157, 126.53306, '2026-04-20', '백록담까지 완등! 날씨 맑아서 뷰가 최고였다.',        5),
    ('00000000-0000-0000-0000-000000000001', '제주 성산일출봉','제주 서귀포시 성산읍 성산리',   33.45843, 126.94238, '2026-04-21', '일출 보러 새벽 5시에 출발. 감동적인 풍경.',           5),
    ('00000000-0000-0000-0000-000000000001', '부산 광안리해수욕장','부산 수영구 광안해변로 219', 35.15340, 129.11839, '2026-05-03', '광안대교 야경이 멋지다. 회 먹고 맥주 한 잔.',        4),
    ('00000000-0000-0000-0000-000000000001', '전주 한옥마을', '전북 전주시 완산구 기린대로 99',35.81530, 127.15313, '2026-05-05', '비빔밥 원조 맛집 발견. 한복 대여해서 사진 찍음.',     4),
    ('00000000-0000-0000-0000-000000000001', '강릉 정동진',   '강원 강릉시 정동진리',          37.68225, 129.01788, '2026-05-08', '해돋이 보러 갔다가 카페에서 커피 한 잔. 여유로웠음.', 4);

-- 장소-카테고리 매핑
INSERT INTO place_category (place_id, category_id)
SELECT p.id, c.id FROM places p, categories c
WHERE p.name = '경복궁'         AND c.name = '관광지'
UNION ALL
SELECT p.id, c.id FROM places p, categories c
WHERE p.name = '남산타워'       AND c.name = '관광지'
UNION ALL
SELECT p.id, c.id FROM places p, categories c
WHERE p.name = '북촌한옥마을'   AND c.name = '관광지'
UNION ALL
SELECT p.id, c.id FROM places p, categories c
WHERE p.name = '광장시장'       AND c.name = '맛집'
UNION ALL
SELECT p.id, c.id FROM places p, categories c
WHERE p.name = '성수동 카페거리' AND c.name = '카페'
UNION ALL
SELECT p.id, c.id FROM places p, categories c
WHERE p.name = '제주 한라산'    AND c.name = '자연'
UNION ALL
SELECT p.id, c.id FROM places p, categories c
WHERE p.name = '제주 성산일출봉' AND c.name = '자연'
UNION ALL
SELECT p.id, c.id FROM places p, categories c
WHERE p.name = '부산 광안리해수욕장' AND c.name = '자연'
UNION ALL
SELECT p.id, c.id FROM places p, categories c
WHERE p.name = '전주 한옥마을'  AND c.name = '관광지'
UNION ALL
SELECT p.id, c.id FROM places p, categories c
WHERE p.name = '강릉 정동진'    AND c.name = '자연';

-- 태그
INSERT INTO place_tags (place_id, tag)
SELECT p.id, t.tag FROM places p,
    (VALUES ('궁궐'), ('역사'), ('봄'), ('서울')) AS t(tag)
WHERE p.name = '경복궁'
UNION ALL
SELECT p.id, t.tag FROM places p,
    (VALUES ('야경'), ('서울'), ('데이트')) AS t(tag)
WHERE p.name = '남산타워'
UNION ALL
SELECT p.id, t.tag FROM places p,
    (VALUES ('제주'), ('등산'), ('자연')) AS t(tag)
WHERE p.name = '제주 한라산';
