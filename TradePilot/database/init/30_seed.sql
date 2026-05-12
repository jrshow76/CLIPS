-- =====================================================
-- TradePilot - 시드 데이터
-- 파일: 30_seed.sql
-- 포함: 섹터 마스터, 시장 지수, 시스템 설정, 데모 사용자
-- =====================================================

-- =====================================================
-- 1. 시장 지수 마스터
-- =====================================================
INSERT INTO tp_market.market_index (code, name, market) VALUES
    ('KOSPI',    '코스피',        'KOSPI'),
    ('KOSDAQ',   '코스닥',        'KOSDAQ'),
    ('KOSPI200', '코스피200',     'KOSPI'),
    ('KRX100',   'KRX100',        'KOSPI')
ON CONFLICT (code) DO NOTHING;

-- =====================================================
-- 2. 섹터 마스터 (KRX 업종 기준 일부 발췌)
-- =====================================================
INSERT INTO tp_market.sectors (code, name, parent_code, sort_order) VALUES
    ('SEC_001', '에너지',          NULL, 1),
    ('SEC_002', '소재',            NULL, 2),
    ('SEC_003', '산업재',          NULL, 3),
    ('SEC_004', '경기관련소비재',  NULL, 4),
    ('SEC_005', '필수소비재',      NULL, 5),
    ('SEC_006', '의료',            NULL, 6),
    ('SEC_007', '금융',            NULL, 7),
    ('SEC_008', 'IT',              NULL, 8),
    ('SEC_009', '커뮤니케이션서비스', NULL, 9),
    ('SEC_010', '유틸리티',        NULL, 10),
    -- 하위 섹터 (예시)
    ('SEC_008_01', '반도체',           'SEC_008', 11),
    ('SEC_008_02', 'IT하드웨어',       'SEC_008', 12),
    ('SEC_008_03', '소프트웨어',       'SEC_008', 13),
    ('SEC_007_01', '은행',             'SEC_007', 14),
    ('SEC_007_02', '증권',             'SEC_007', 15),
    ('SEC_007_03', '보험',             'SEC_007', 16),
    ('SEC_006_01', '제약/바이오',      'SEC_006', 17)
ON CONFLICT (code) DO NOTHING;

-- =====================================================
-- 3. 데모 사용자 (비밀번호: Demo!2026 의 bcrypt 해시는 백엔드에서 갱신)
--    초기 비밀번호 해시는 더미('!') - 운영 시 반드시 교체
-- =====================================================
INSERT INTO tp_user.users (email, password_hash, nickname, role, trade_mode, email_verified, phone_verified)
VALUES
    ('admin@tradepilot.local',     '!', '관리자',      'ROLE_ADMIN',       'SIM', TRUE,  TRUE),
    ('operator@tradepilot.local',  '!', '운영자',      'ROLE_OPERATOR',    'SIM', TRUE,  TRUE),
    ('demo_pro@tradepilot.local',  '!', '데모프로',    'ROLE_TRADER_PRO',  'SIM', TRUE,  TRUE),
    ('demo@tradepilot.local',      '!', '데모유저',    'ROLE_TRADER',      'SIM', TRUE,  FALSE),
    ('guest@tradepilot.local',     '!', '게스트',      'ROLE_GUEST',       'SIM', FALSE, FALSE)
ON CONFLICT (email) DO NOTHING;

-- 데모 사용자 프로필/설정
INSERT INTO tp_user.user_profiles (user_id, timezone, locale)
SELECT id, 'Asia/Seoul', 'ko-KR' FROM tp_user.users
WHERE email IN ('admin@tradepilot.local','operator@tradepilot.local','demo_pro@tradepilot.local','demo@tradepilot.local','guest@tradepilot.local')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO tp_user.user_settings (user_id, theme, noti_inapp, noti_email)
SELECT id, 'light', TRUE, TRUE FROM tp_user.users
WHERE email IN ('admin@tradepilot.local','operator@tradepilot.local','demo_pro@tradepilot.local','demo@tradepilot.local','guest@tradepilot.local')
ON CONFLICT (user_id) DO NOTHING;

-- 데모 사용자 한도 설정(정책 기본값)
INSERT INTO tp_trade.trade_limits (user_id)
SELECT id FROM tp_user.users
WHERE email IN ('demo_pro@tradepilot.local','demo@tradepilot.local')
ON CONFLICT (user_id) DO NOTHING;

-- 알림 채널 기본값
INSERT INTO tp_notify.notification_channels (user_id, inapp_enabled, email_enabled, telegram_enabled)
SELECT id, TRUE, TRUE, FALSE FROM tp_user.users
WHERE email IN ('admin@tradepilot.local','operator@tradepilot.local','demo_pro@tradepilot.local','demo@tradepilot.local','guest@tradepilot.local')
ON CONFLICT (user_id) DO NOTHING;

-- =====================================================
-- 4. 종목 마스터 (예시 10종목 - 초기 부트스트랩용)
-- =====================================================
INSERT INTO tp_market.stocks (code, name, market, status, market_cap) VALUES
    ('005930', '삼성전자',         'KOSPI',  'LISTED', 450000000000000),
    ('000660', 'SK하이닉스',       'KOSPI',  'LISTED', 100000000000000),
    ('035420', 'NAVER',            'KOSPI',  'LISTED',  35000000000000),
    ('035720', '카카오',           'KOSPI',  'LISTED',  20000000000000),
    ('051910', 'LG화학',           'KOSPI',  'LISTED',  35000000000000),
    ('068270', '셀트리온',         'KOSPI',  'LISTED',  30000000000000),
    ('005380', '현대차',           'KOSPI',  'LISTED',  40000000000000),
    ('373220', 'LG에너지솔루션',   'KOSPI',  'LISTED',  90000000000000),
    ('086520', '에코프로',         'KOSDAQ', 'LISTED',  10000000000000),
    ('247540', '에코프로비엠',     'KOSDAQ', 'LISTED',  15000000000000)
ON CONFLICT (code) DO NOTHING;

-- 종목 ↔ 섹터 매핑 (대표 섹터 1개씩)
INSERT INTO tp_market.stock_sectors (stock_id, sector_id, is_primary)
SELECT s.id, sec.id, TRUE
FROM tp_market.stocks s
JOIN tp_market.sectors sec ON sec.code =
    CASE s.code
        WHEN '005930' THEN 'SEC_008_01'  -- 삼성전자 → 반도체
        WHEN '000660' THEN 'SEC_008_01'  -- SK하이닉스 → 반도체
        WHEN '035420' THEN 'SEC_008_03'  -- NAVER → 소프트웨어
        WHEN '035720' THEN 'SEC_008_03'  -- 카카오 → 소프트웨어
        WHEN '051910' THEN 'SEC_002'     -- LG화학 → 소재
        WHEN '068270' THEN 'SEC_006_01'  -- 셀트리온 → 제약/바이오
        WHEN '005380' THEN 'SEC_004'     -- 현대차 → 경기관련소비재
        WHEN '373220' THEN 'SEC_002'     -- LG에너지솔루션 → 소재(2차전지)
        WHEN '086520' THEN 'SEC_002'     -- 에코프로 → 소재
        WHEN '247540' THEN 'SEC_002'     -- 에코프로비엠 → 소재
    END
ON CONFLICT (stock_id, sector_id) DO NOTHING;

-- =====================================================
-- 5. 시스템 시드 데이터 확인 쿼리 (코멘트)
-- =====================================================
-- SELECT 'users' as t, COUNT(*) FROM tp_user.users
-- UNION ALL SELECT 'sectors', COUNT(*) FROM tp_market.sectors
-- UNION ALL SELECT 'stocks',  COUNT(*) FROM tp_market.stocks
-- UNION ALL SELECT 'indices', COUNT(*) FROM tp_market.market_index;
