-- =============================================================================
-- Shelfy - V1: 초기 스키마 (Init Schema)
-- 작성일: 2026-05-09
-- 작성자: DBA
-- 대상 DB: PostgreSQL 15+
-- 마이그레이션 도구: Flyway (버전 관리 기반)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 사전 설정
-- -----------------------------------------------------------------------------

-- pg_trgm: 전문 검색 보조 (LIKE 인덱스 활용)
-- unaccent: 다국어 검색 정규화 (향후 확장 대비)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- 한국어 전문 검색용 텍스트 검색 설정 (simple 설정 사용 - 형태소 분석 없이 어절 단위)
-- 운영 환경에서 pg_bigm 설치 시 bigm 인덱스로 교체 권장
-- 현재는 to_tsvector('simple', ...) 방식으로 운용

-- -----------------------------------------------------------------------------
-- ENUM 타입 정의
-- PostgreSQL 네이티브 ENUM 대신 CHECK 제약조건을 사용한다.
-- 사유: ENUM 타입은 ALTER TYPE으로 값 추가 시 테이블 전체 재작성이 필요하여
--       운영 중 배포 리스크가 높다. VARCHAR + CHECK로 유연성을 확보한다.
-- -----------------------------------------------------------------------------

-- -----------------------------------------------------------------------------
-- 1. files (업로드 파일)
-- 순환 참조 방지를 위해 users보다 먼저 생성한다.
-- users.profile_image_id -> files.id (DEFERRABLE FK로 처리)
-- -----------------------------------------------------------------------------
CREATE TABLE files (
    id              BIGSERIAL       NOT NULL,
    uploader_id     BIGINT          NOT NULL,
    file_type       VARCHAR(20)     NOT NULL,
    original_name   VARCHAR(255)    NOT NULL,
    stored_name     VARCHAR(255)    NOT NULL,
    cdn_url         VARCHAR(500)    NOT NULL,
    file_size       BIGINT          NOT NULL,
    mime_type       VARCHAR(50)     NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_files PRIMARY KEY (id),
    CONSTRAINT uq_files_stored_name UNIQUE (stored_name),
    CONSTRAINT chk_files_file_type CHECK (
        file_type IN ('ITEM_IMAGE', 'PROFILE_IMAGE')
    ),
    CONSTRAINT chk_files_file_size CHECK (file_size > 0),
    CONSTRAINT chk_files_mime_type CHECK (
        mime_type IN ('image/jpeg', 'image/png', 'image/webp')
    )
);

COMMENT ON TABLE  files IS '업로드된 파일 메타데이터';
COMMENT ON COLUMN files.id IS '파일 ID (PK)';
COMMENT ON COLUMN files.uploader_id IS '업로드한 사용자 ID (users.id FK, 순환참조로 인해 DDL 후 추가)';
COMMENT ON COLUMN files.file_type IS '파일 유형: ITEM_IMAGE / PROFILE_IMAGE';
COMMENT ON COLUMN files.stored_name IS 'UUID 기반 저장 파일명 (CDN 경로 키)';
COMMENT ON COLUMN files.cdn_url IS 'CDN 접근 URL';
COMMENT ON COLUMN files.file_size IS '파일 크기 (bytes)';

-- -----------------------------------------------------------------------------
-- 2. users (사용자)
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id                  BIGSERIAL       NOT NULL,
    email               VARCHAR(255)    NOT NULL,
    password_hash       VARCHAR(255)    NOT NULL,
    nickname            VARCHAR(20)     NOT NULL,
    bio                 VARCHAR(200),
    profile_image_id    BIGINT,
    email_verified      BOOLEAN         NOT NULL DEFAULT FALSE,
    agree_terms         BOOLEAN         NOT NULL,
    agree_privacy       BOOLEAN         NOT NULL,
    agree_marketing     BOOLEAN         NOT NULL DEFAULT FALSE,
    login_failed_count  SMALLINT        NOT NULL DEFAULT 0,
    locked_until        TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_nickname UNIQUE (nickname),
    CONSTRAINT chk_users_email_length CHECK (char_length(email) >= 5),
    CONSTRAINT chk_users_nickname_length CHECK (
        char_length(nickname) BETWEEN 2 AND 20
    ),
    CONSTRAINT chk_users_login_failed_count CHECK (
        login_failed_count >= 0 AND login_failed_count <= 10
    ),
    CONSTRAINT chk_users_agree_terms CHECK (agree_terms = TRUE),
    CONSTRAINT chk_users_agree_privacy CHECK (agree_privacy = TRUE),
    CONSTRAINT fk_users_profile_image FOREIGN KEY (profile_image_id)
        REFERENCES files (id)
        ON DELETE SET NULL
        DEFERRABLE INITIALLY DEFERRED
);

COMMENT ON TABLE  users IS '사용자 계정';
COMMENT ON COLUMN users.id IS '사용자 ID (PK, BIGSERIAL)';
COMMENT ON COLUMN users.email IS '이메일 (로그인 ID, UNIQUE)';
COMMENT ON COLUMN users.password_hash IS 'bcrypt 해시 비밀번호 (라운드 12 이상 권장)';
COMMENT ON COLUMN users.nickname IS '닉네임 (공개, UNIQUE, 2~20자)';
COMMENT ON COLUMN users.email_verified IS '이메일 인증 완료 여부. false 상태에서 셀러 기능 제한';
COMMENT ON COLUMN users.login_failed_count IS '연속 로그인 실패 횟수. 5회 초과 시 locked_until 설정';
COMMENT ON COLUMN users.locked_until IS '계정 잠금 해제 시각. NULL이면 잠금 없음';
COMMENT ON COLUMN users.deleted_at IS '소프트 삭제 시각. NULL이면 정상 계정';

-- files.uploader_id -> users.id FK (순환참조 해결을 위해 users 생성 후 추가)
ALTER TABLE files
    ADD CONSTRAINT fk_files_uploader
        FOREIGN KEY (uploader_id)
        REFERENCES users (id)
        ON DELETE RESTRICT;

-- -----------------------------------------------------------------------------
-- 3. email_verifications (이메일 인증)
-- -----------------------------------------------------------------------------
CREATE TABLE email_verifications (
    id              BIGSERIAL       NOT NULL,
    user_id         BIGINT          NOT NULL,
    token           VARCHAR(255)    NOT NULL,
    expires_at      TIMESTAMPTZ     NOT NULL,
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_email_verifications PRIMARY KEY (id),
    CONSTRAINT uq_email_verifications_token UNIQUE (token),
    CONSTRAINT fk_email_verifications_user FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE,
    CONSTRAINT chk_email_verifications_expires CHECK (expires_at > created_at)
);

COMMENT ON TABLE  email_verifications IS '이메일 인증 토큰 (발급 후 24시간 유효)';
COMMENT ON COLUMN email_verifications.token IS '인증 토큰 (UUID v4 권장)';
COMMENT ON COLUMN email_verifications.expires_at IS '만료 시각 (발급 시점 + 24시간)';
COMMENT ON COLUMN email_verifications.verified_at IS '인증 완료 시각. NULL이면 미인증';

-- -----------------------------------------------------------------------------
-- 4. password_reset_tokens (비밀번호 재설정 토큰)
-- -----------------------------------------------------------------------------
CREATE TABLE password_reset_tokens (
    id              BIGSERIAL       NOT NULL,
    user_id         BIGINT          NOT NULL,
    token           VARCHAR(255)    NOT NULL,
    expires_at      TIMESTAMPTZ     NOT NULL,
    used_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_password_reset_tokens PRIMARY KEY (id),
    CONSTRAINT uq_password_reset_tokens_token UNIQUE (token),
    CONSTRAINT fk_password_reset_tokens_user FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE,
    CONSTRAINT chk_password_reset_tokens_expires CHECK (expires_at > created_at)
);

COMMENT ON TABLE  password_reset_tokens IS '비밀번호 재설정 토큰 (발급 후 1시간 유효, 1회 사용)';
COMMENT ON COLUMN password_reset_tokens.used_at IS '사용 완료 시각. NULL이면 미사용';

-- -----------------------------------------------------------------------------
-- 5. refresh_tokens (리프레시 토큰)
-- -----------------------------------------------------------------------------
CREATE TABLE refresh_tokens (
    id              BIGSERIAL       NOT NULL,
    user_id         BIGINT          NOT NULL,
    token_hash      VARCHAR(255)    NOT NULL,
    expires_at      TIMESTAMPTZ     NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_refresh_tokens PRIMARY KEY (id),
    CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE,
    CONSTRAINT chk_refresh_tokens_expires CHECK (expires_at > created_at)
);

COMMENT ON TABLE  refresh_tokens IS '리프레시 토큰 (14일 유효, HttpOnly 쿠키로 전달)';
COMMENT ON COLUMN refresh_tokens.token_hash IS 'SHA-256 해시된 토큰값 (원본 토큰 미저장)';
COMMENT ON COLUMN refresh_tokens.revoked_at IS '무효화 시각. NULL이면 유효한 토큰';

-- -----------------------------------------------------------------------------
-- 6. items (상품)
-- tsvector 전문 검색 컬럼: title + description + tags를 단일 컬럼으로 관리
-- 트리거로 자동 갱신 (애플리케이션 코드와 분리)
-- -----------------------------------------------------------------------------
CREATE TABLE items (
    id                  BIGSERIAL       NOT NULL,
    seller_id           BIGINT          NOT NULL,
    title               VARCHAR(100)    NOT NULL,
    description         TEXT            NOT NULL,
    category            VARCHAR(30)     NOT NULL,
    sale_type           VARCHAR(10)     NOT NULL,
    price               INTEGER,
    thumbnail_image_id  BIGINT,
    tags                VARCHAR(20)[]   NOT NULL DEFAULT '{}',
    status              VARCHAR(10)     NOT NULL DEFAULT 'DRAFT',
    view_count          BIGINT          NOT NULL DEFAULT 0,
    -- 전문 검색용 tsvector (트리거로 자동 관리)
    search_vector       TSVECTOR,
    deleted_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_items PRIMARY KEY (id),
    CONSTRAINT fk_items_seller FOREIGN KEY (seller_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_items_thumbnail FOREIGN KEY (thumbnail_image_id)
        REFERENCES files (id)
        ON DELETE SET NULL,
    CONSTRAINT chk_items_category CHECK (
        category IN (
            'DIGITAL_CONTENT', 'COURSE', 'TEMPLATE',
            'PHOTO', 'MUSIC', 'SOFTWARE', 'OTHER'
        )
    ),
    CONSTRAINT chk_items_sale_type CHECK (
        sale_type IN ('PURCHASE', 'SUBSCRIBE', 'BOTH')
    ),
    CONSTRAINT chk_items_status CHECK (
        status IN ('DRAFT', 'PUBLISHED')
    ),
    -- 단일 구매 가능 상품은 price 필수
    CONSTRAINT chk_items_price_required CHECK (
        (sale_type = 'SUBSCRIBE') OR (price IS NOT NULL)
    ),
    -- 가격 범위: 100원 이상 10,000,000원 이하
    CONSTRAINT chk_items_price_range CHECK (
        price IS NULL OR (price >= 100 AND price <= 10000000)
    ),
    CONSTRAINT chk_items_view_count CHECK (view_count >= 0),
    -- 태그 개수 제한: 최대 10개
    CONSTRAINT chk_items_tags_count CHECK (array_length(tags, 1) IS NULL OR array_length(tags, 1) <= 10),
    CONSTRAINT chk_items_title_length CHECK (char_length(title) BETWEEN 2 AND 100),
    CONSTRAINT chk_items_description_length CHECK (char_length(description) >= 10)
);

COMMENT ON TABLE  items IS '상품 (셀러가 선반에 등록한 아이템)';
COMMENT ON COLUMN items.sale_type IS '판매 유형: PURCHASE(단건) / SUBSCRIBE(구독) / BOTH(모두)';
COMMENT ON COLUMN items.price IS '단일 구매 가격. SUBSCRIBE 전용 상품은 NULL 허용';
COMMENT ON COLUMN items.tags IS 'PostgreSQL 배열 타입. GIN 인덱스로 검색';
COMMENT ON COLUMN items.status IS '상품 상태: DRAFT(비공개) / PUBLISHED(공개)';
COMMENT ON COLUMN items.search_vector IS '전문 검색용 tsvector. 트리거로 자동 갱신 (title 가중치 A, description 가중치 B, tags 가중치 C)';
COMMENT ON COLUMN items.view_count IS '조회수. 빈번한 UPDATE 부하 완화를 위해 비동기 배치 갱신 권장';

-- items.search_vector 자동 갱신 함수
CREATE OR REPLACE FUNCTION fn_items_search_vector_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.search_vector :=
        -- title: 가중치 A (최고 우선순위)
        setweight(to_tsvector('simple', coalesce(NEW.title, '')), 'A') ||
        -- description: 가중치 B
        setweight(to_tsvector('simple', coalesce(NEW.description, '')), 'B') ||
        -- tags 배열: 가중치 C (배열을 공백 구분 문자열로 변환)
        setweight(to_tsvector('simple', coalesce(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION fn_items_search_vector_update() IS
    'items INSERT/UPDATE 시 search_vector를 자동 갱신하는 트리거 함수. '
    'title(A) > description(B) > tags(C) 순서로 검색 가중치 부여';

CREATE TRIGGER trg_items_search_vector_update
    BEFORE INSERT OR UPDATE OF title, description, tags
    ON items
    FOR EACH ROW
    EXECUTE FUNCTION fn_items_search_vector_update();

-- -----------------------------------------------------------------------------
-- 7. item_images (상품 이미지)
-- -----------------------------------------------------------------------------
CREATE TABLE item_images (
    id              BIGSERIAL       NOT NULL,
    item_id         BIGINT          NOT NULL,
    file_id         BIGINT          NOT NULL,
    sort_order      SMALLINT        NOT NULL DEFAULT 0,
    is_thumbnail    BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_item_images PRIMARY KEY (id),
    CONSTRAINT fk_item_images_item FOREIGN KEY (item_id)
        REFERENCES items (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_item_images_file FOREIGN KEY (file_id)
        REFERENCES files (id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_item_images_sort_order CHECK (sort_order >= 0),
    -- 동일 아이템 내 sort_order 중복 방지
    CONSTRAINT uq_item_images_sort_order UNIQUE (item_id, sort_order)
);

COMMENT ON TABLE  item_images IS '상품 이미지 목록 (최대 10장)';
COMMENT ON COLUMN item_images.sort_order IS '이미지 정렬 순서 (0부터 시작). item_id 내에서 UNIQUE';
COMMENT ON COLUMN item_images.is_thumbnail IS '대표 이미지 여부. items.thumbnail_image_id와 함께 관리';

-- 썸네일은 item_id당 1개만 허용하는 부분 UNIQUE 인덱스
-- (is_thumbnail = true인 행은 item_id별로 하나만 존재 가능)
CREATE UNIQUE INDEX uq_item_images_thumbnail
    ON item_images (item_id)
    WHERE is_thumbnail = TRUE;

-- -----------------------------------------------------------------------------
-- 8. subscription_plans (구독 플랜)
-- -----------------------------------------------------------------------------
CREATE TABLE subscription_plans (
    id              BIGSERIAL       NOT NULL,
    item_id         BIGINT          NOT NULL,
    plan_name       VARCHAR(50)     NOT NULL,
    period          VARCHAR(10)     NOT NULL,
    plan_price      INTEGER         NOT NULL,
    description     VARCHAR(500),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_subscription_plans PRIMARY KEY (id),
    CONSTRAINT fk_subscription_plans_item FOREIGN KEY (item_id)
        REFERENCES items (id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_subscription_plans_period CHECK (
        period IN ('MONTHLY', 'QUARTERLY', 'YEARLY')
    ),
    CONSTRAINT chk_subscription_plans_price CHECK (plan_price >= 100),
    CONSTRAINT chk_subscription_plans_plan_name_length CHECK (
        char_length(plan_name) BETWEEN 2 AND 50
    ),
    -- 동일 상품에 동일 period + plan_name 중복 방지 (is_active 무관)
    CONSTRAINT uq_subscription_plans_item_period_name UNIQUE (item_id, period, plan_name)
);

COMMENT ON TABLE  subscription_plans IS '상품별 구독 플랜 (Basic, Premium 등)';
COMMENT ON COLUMN subscription_plans.period IS '구독 주기: MONTHLY / QUARTERLY / YEARLY';
COMMENT ON COLUMN subscription_plans.plan_price IS '구독 가격. 활성 구독자 존재 시 변경 불가 (애플리케이션 제어)';
COMMENT ON COLUMN subscription_plans.is_active IS '플랜 활성 여부. false이면 신규 구독 불가 (기존 구독 유지)';

-- -----------------------------------------------------------------------------
-- 9. orders (구매 주문)
-- 데이터 보존 정책: 전자상거래법 5년 보존. 물리 삭제 없음.
-- -----------------------------------------------------------------------------
CREATE TABLE orders (
    id                  BIGSERIAL       NOT NULL,
    buyer_id            BIGINT          NOT NULL,
    item_id             BIGINT          NOT NULL,
    -- 주문 시점 스냅샷 (상품 수정 후에도 주문 내역 보존)
    item_title          VARCHAR(100)    NOT NULL,
    amount              INTEGER         NOT NULL,
    payment_method      VARCHAR(20)     NOT NULL,
    pg_transaction_id   VARCHAR(255),
    status              VARCHAR(20)     NOT NULL,
    refund_reason       VARCHAR(500),
    refunded_at         TIMESTAMPTZ,
    paid_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_orders PRIMARY KEY (id),
    CONSTRAINT uq_orders_pg_transaction_id UNIQUE (pg_transaction_id),
    CONSTRAINT fk_orders_buyer FOREIGN KEY (buyer_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_orders_item FOREIGN KEY (item_id)
        REFERENCES items (id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_orders_payment_method CHECK (
        payment_method IN ('CARD', 'KAKAO_PAY', 'NAVER_PAY')
    ),
    CONSTRAINT chk_orders_status CHECK (
        status IN ('PENDING', 'COMPLETED', 'REFUNDED', 'FAILED')
    ),
    CONSTRAINT chk_orders_amount CHECK (amount > 0),
    -- 환불 상태인 경우 refunded_at 필수
    CONSTRAINT chk_orders_refunded_at CHECK (
        status != 'REFUNDED' OR refunded_at IS NOT NULL
    ),
    -- COMPLETED 상태인 경우 paid_at 필수
    CONSTRAINT chk_orders_paid_at CHECK (
        status NOT IN ('COMPLETED', 'REFUNDED') OR paid_at IS NOT NULL
    )
);

COMMENT ON TABLE  orders IS '구매 주문 (단일 구매). 전자상거래법 5년 보존 대상';
COMMENT ON COLUMN orders.item_title IS '주문 시점 상품명 스냅샷 (상품 수정 후에도 이력 보존)';
COMMENT ON COLUMN orders.amount IS '실제 결제 금액 (플랫폼 수수료 포함)';
COMMENT ON COLUMN orders.pg_transaction_id IS 'PG사 거래 ID. UNIQUE (NULL 허용 - 결제 전 PENDING 상태)';

-- -----------------------------------------------------------------------------
-- 10. subscriptions (구독)
-- -----------------------------------------------------------------------------
CREATE TABLE subscriptions (
    id                  BIGSERIAL       NOT NULL,
    subscriber_id       BIGINT          NOT NULL,
    item_id             BIGINT          NOT NULL,
    plan_id             BIGINT          NOT NULL,
    -- 구독 시점 스냅샷
    plan_name           VARCHAR(50)     NOT NULL,
    amount              INTEGER         NOT NULL,
    payment_method      VARCHAR(20)     NOT NULL,
    status              VARCHAR(20)     NOT NULL,
    started_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    next_billing_at     TIMESTAMPTZ     NOT NULL,
    cancelled_at        TIMESTAMPTZ,
    active_until        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_subscriptions PRIMARY KEY (id),
    CONSTRAINT fk_subscriptions_subscriber FOREIGN KEY (subscriber_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_subscriptions_item FOREIGN KEY (item_id)
        REFERENCES items (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_subscriptions_plan FOREIGN KEY (plan_id)
        REFERENCES subscription_plans (id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_subscriptions_payment_method CHECK (
        payment_method IN ('CARD', 'KAKAO_PAY', 'NAVER_PAY')
    ),
    CONSTRAINT chk_subscriptions_status CHECK (
        status IN ('ACTIVE', 'CANCEL_REQUESTED', 'CANCELLED', 'SUSPENDED')
    ),
    CONSTRAINT chk_subscriptions_amount CHECK (amount > 0),
    CONSTRAINT chk_subscriptions_next_billing CHECK (
        next_billing_at > started_at
    ),
    -- 해지 신청 또는 해지 완료 상태인 경우 cancelled_at 필수
    CONSTRAINT chk_subscriptions_cancelled_at CHECK (
        status NOT IN ('CANCEL_REQUESTED', 'CANCELLED') OR cancelled_at IS NOT NULL
    )
);

COMMENT ON TABLE  subscriptions IS '구독 현황. 동일 subscriber_id + item_id 활성 구독은 1건만 허용 (애플리케이션 제어)';
COMMENT ON COLUMN subscriptions.plan_name IS '구독 시점 플랜명 스냅샷';
COMMENT ON COLUMN subscriptions.next_billing_at IS '다음 결제 예정 일시. 정기 결제 배치가 이 컬럼을 기준으로 실행';
COMMENT ON COLUMN subscriptions.active_until IS '서비스 이용 가능 만료 시각. CANCEL_REQUESTED 상태에서 세팅';

-- 동일 사용자가 동일 상품에 ACTIVE 또는 CANCEL_REQUESTED 구독을 중복으로 갖지 못하도록 부분 UNIQUE 인덱스
CREATE UNIQUE INDEX uq_subscriptions_active_per_user_item
    ON subscriptions (subscriber_id, item_id)
    WHERE status IN ('ACTIVE', 'CANCEL_REQUESTED');

COMMENT ON INDEX uq_subscriptions_active_per_user_item IS
    '활성/해지신청 상태의 구독은 동일 사용자+상품 조합에서 1건만 허용';

-- -----------------------------------------------------------------------------
-- 11. subscription_payments (구독 결제 이력)
-- 데이터 보존 정책: 전자상거래법 5년 보존. 물리 삭제 없음.
-- 파티셔닝 검토: 현재는 단일 테이블로 운영. 연간 결제 건수가 100만 건 초과 시
--               created_at 기준 Range 파티셔닝(연간) 전환을 권장한다.
-- -----------------------------------------------------------------------------
CREATE TABLE subscription_payments (
    id                  BIGSERIAL       NOT NULL,
    subscription_id     BIGINT          NOT NULL,
    amount              INTEGER         NOT NULL,
    pg_transaction_id   VARCHAR(255),
    status              VARCHAR(20)     NOT NULL,
    billing_at          TIMESTAMPTZ     NOT NULL,
    paid_at             TIMESTAMPTZ,
    failed_reason       VARCHAR(255),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_subscription_payments PRIMARY KEY (id),
    CONSTRAINT uq_subscription_payments_pg_transaction_id UNIQUE (pg_transaction_id),
    CONSTRAINT fk_subscription_payments_subscription FOREIGN KEY (subscription_id)
        REFERENCES subscriptions (id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_subscription_payments_status CHECK (
        status IN ('SUCCESS', 'FAILED')
    ),
    CONSTRAINT chk_subscription_payments_amount CHECK (amount > 0),
    -- 성공 상태인 경우 paid_at 및 pg_transaction_id 필수
    CONSTRAINT chk_subscription_payments_paid_at CHECK (
        status != 'SUCCESS' OR (paid_at IS NOT NULL AND pg_transaction_id IS NOT NULL)
    ),
    -- 실패 상태인 경우 failed_reason 권장 (NOT NULL 강제 미적용 - 외부 PG사 응답 지연 가능성)
    CONSTRAINT chk_subscription_payments_billing_at CHECK (billing_at IS NOT NULL)
);

COMMENT ON TABLE  subscription_payments IS '구독 정기 결제 이력. 전자상거래법 5년 보존 대상';
COMMENT ON COLUMN subscription_payments.billing_at IS '결제 예정 일시 (배치 기준값)';
COMMENT ON COLUMN subscription_payments.paid_at IS '실제 결제 완료 일시';

-- =============================================================================
-- 인덱스 정의
-- (인덱스 설계 근거는 /docs/dba/index-design.md 참조)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- users 인덱스
-- -----------------------------------------------------------------------------

-- UNIQUE 인덱스는 제약조건 선언으로 자동 생성됨 (email, nickname)

-- 소프트 삭제 필터 + 잠금 해제 시각 조회
-- WHERE deleted_at IS NULL 조건이 대부분의 쿼리에 포함되므로 부분 인덱스 적용
CREATE INDEX idx_users_active
    ON users (created_at DESC)
    WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_users_active IS
    '정상 사용자 대상 쿼리 최적화. deleted_at IS NULL 부분 인덱스로 삭제된 계정 제외';

-- 계정 잠금 해제 배치 처리용
CREATE INDEX idx_users_locked
    ON users (locked_until)
    WHERE locked_until IS NOT NULL AND deleted_at IS NULL;

COMMENT ON INDEX idx_users_locked IS
    '잠금된 계정 배치 해제 처리용. locked_until IS NOT NULL 조건만 스캔';

-- -----------------------------------------------------------------------------
-- email_verifications 인덱스
-- -----------------------------------------------------------------------------

-- user_id 조회 (최신 토큰 우선)
CREATE INDEX idx_email_verifications_user_id
    ON email_verifications (user_id, created_at DESC);

-- 만료된 미인증 토큰 배치 삭제용 부분 인덱스
CREATE INDEX idx_email_verifications_cleanup
    ON email_verifications (expires_at)
    WHERE verified_at IS NULL;

COMMENT ON INDEX idx_email_verifications_cleanup IS
    '만료된 미인증 토큰 배치 삭제용. verified_at IS NULL인 행만 인덱싱';

-- -----------------------------------------------------------------------------
-- refresh_tokens 인덱스
-- -----------------------------------------------------------------------------

-- 토큰 검증용 UNIQUE 인덱스는 제약조건으로 자동 생성됨 (token_hash)

-- user_id별 유효 토큰 조회 (로그아웃, 토큰 무효화)
CREATE INDEX idx_refresh_tokens_user_id_active
    ON refresh_tokens (user_id, expires_at DESC)
    WHERE revoked_at IS NULL;

COMMENT ON INDEX idx_refresh_tokens_user_id_active IS
    '사용자별 유효 리프레시 토큰 조회. 로그아웃, 다중 기기 무효화 처리에 활용';

-- 만료 토큰 배치 정리용
CREATE INDEX idx_refresh_tokens_cleanup
    ON refresh_tokens (expires_at)
    WHERE revoked_at IS NULL;

-- -----------------------------------------------------------------------------
-- items 인덱스
-- -----------------------------------------------------------------------------

-- [핵심 인덱스 1] 공개 상품 목록 탐색 - category 필터 + 최신순/가격순 정렬
-- WHERE status = 'PUBLISHED' AND deleted_at IS NULL 조건 부분 인덱스
CREATE INDEX idx_items_browse_category_latest
    ON items (category, created_at DESC)
    WHERE status = 'PUBLISHED' AND deleted_at IS NULL;

COMMENT ON INDEX idx_items_browse_category_latest IS
    '카테고리별 공개 상품 최신순 조회. 가장 빈번한 탐색 패턴 (GET /items?category=...)';

-- [핵심 인덱스 2] 공개 상품 가격 범위 필터 + 정렬
CREATE INDEX idx_items_browse_price
    ON items (price ASC, created_at DESC)
    WHERE status = 'PUBLISHED' AND deleted_at IS NULL AND price IS NOT NULL;

COMMENT ON INDEX idx_items_browse_price IS
    '가격 범위 필터 및 가격순 정렬. minPrice/maxPrice 파라미터 처리';

-- [핵심 인덱스 3] 인기순 정렬 (view_count DESC)
CREATE INDEX idx_items_browse_popular
    ON items (view_count DESC, created_at DESC)
    WHERE status = 'PUBLISHED' AND deleted_at IS NULL;

COMMENT ON INDEX idx_items_browse_popular IS
    '인기순(조회수) 정렬. sort=popular 파라미터 처리';

-- [핵심 인덱스 4] 셀러별 상품 조회 (내 상품 목록 / 셀러 프로필)
CREATE INDEX idx_items_seller_id
    ON items (seller_id, created_at DESC)
    WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_items_seller_id IS
    '셀러별 상품 조회 (GET /items/my, GET /users/{nickname}/profile). deleted_at IS NULL 부분 인덱스';

-- [핵심 인덱스 5] 전문 검색 GIN 인덱스
CREATE INDEX idx_items_search_vector
    ON items USING GIN (search_vector);

COMMENT ON INDEX idx_items_search_vector IS
    '전문 검색용 GIN 인덱스. to_tsquery()를 사용한 키워드 검색 (GET /items/search)';

-- [핵심 인덱스 6] 태그 GIN 인덱스 (배열 검색)
CREATE INDEX idx_items_tags
    ON items USING GIN (tags);

COMMENT ON INDEX idx_items_tags IS
    '태그 배열 검색용 GIN 인덱스. WHERE tags @> ARRAY[''태그명''] 패턴 지원';

-- [핵심 인덱스 7] sale_type 필터 (SUBSCRIBE/PURCHASE/BOTH)
CREATE INDEX idx_items_sale_type
    ON items (sale_type, created_at DESC)
    WHERE status = 'PUBLISHED' AND deleted_at IS NULL;

-- -----------------------------------------------------------------------------
-- orders 인덱스
-- -----------------------------------------------------------------------------

-- [핵심 인덱스] 구매자별 주문 이력 조회 (가장 빈번한 패턴)
CREATE INDEX idx_orders_buyer_id
    ON orders (buyer_id, created_at DESC);

COMMENT ON INDEX idx_orders_buyer_id IS
    '구매자별 주문 이력 조회 (GET /orders). paid_at 날짜 범위 필터는 추가 조건으로 처리';

-- 날짜 범위 필터 조합 인덱스
CREATE INDEX idx_orders_buyer_paid_at
    ON orders (buyer_id, paid_at DESC)
    WHERE paid_at IS NOT NULL;

COMMENT ON INDEX idx_orders_buyer_paid_at IS
    '날짜 범위 기반 구매 내역 조회 (startDate/endDate 파라미터). paid_at IS NOT NULL 부분 인덱스';

-- 상품별 주문 집계 (셀러 수익 현황)
CREATE INDEX idx_orders_item_id
    ON orders (item_id, status, paid_at DESC);

COMMENT ON INDEX idx_orders_item_id IS
    '상품별 주문 집계. 셀러 수익 현황 쿼리 (GET /users/me/revenue) 최적화';

-- PENDING 상태 주문 모니터링 (배치 정리, 결제 검증)
CREATE INDEX idx_orders_pending
    ON orders (created_at DESC)
    WHERE status = 'PENDING';

-- -----------------------------------------------------------------------------
-- subscriptions 인덱스
-- -----------------------------------------------------------------------------

-- [핵심 인덱스 1] 구독자별 구독 이력 조회
CREATE INDEX idx_subscriptions_subscriber_id
    ON subscriptions (subscriber_id, created_at DESC);

COMMENT ON INDEX idx_subscriptions_subscriber_id IS
    '구독자별 구독 이력 전체 조회 (GET /subscriptions). status 필터는 추가 조건';

-- [핵심 인덱스 2] 활성 구독 필터 (구독 중복 체크, 상태 전이)
CREATE INDEX idx_subscriptions_subscriber_active
    ON subscriptions (subscriber_id, item_id)
    WHERE status IN ('ACTIVE', 'CANCEL_REQUESTED');

COMMENT ON INDEX idx_subscriptions_subscriber_active IS
    '활성/해지신청 구독 중복 체크용. uq_subscriptions_active_per_user_item 부분 UNIQUE 인덱스와 동일 조건';

-- [핵심 인덱스 3] 정기 결제 배치 처리 (가장 중요한 배치 쿼리)
-- 배치: ACTIVE 상태이면서 next_billing_at이 현재 시각 이전인 구독 조회
CREATE INDEX idx_subscriptions_billing_batch
    ON subscriptions (next_billing_at ASC)
    WHERE status = 'ACTIVE';

COMMENT ON INDEX idx_subscriptions_billing_batch IS
    '정기 결제 배치 처리용. status=ACTIVE 부분 인덱스로 최소 행만 스캔. '
    'WHERE status = ''ACTIVE'' AND next_billing_at <= NOW() 패턴';

-- [핵심 인덱스 4] 상품별 구독자 집계 (셀러 수익 현황)
CREATE INDEX idx_subscriptions_item_id_status
    ON subscriptions (item_id, status);

COMMENT ON INDEX idx_subscriptions_item_id_status IS
    '상품별 활성 구독자 수 집계. GET /users/me/revenue의 activeSubscribers 집계 최적화';

-- 해지 만료 배치 (CANCEL_REQUESTED -> CANCELLED 상태 전이)
CREATE INDEX idx_subscriptions_cancel_expiry
    ON subscriptions (active_until ASC)
    WHERE status = 'CANCEL_REQUESTED';

COMMENT ON INDEX idx_subscriptions_cancel_expiry IS
    '해지 신청 구독의 만료 처리 배치. active_until <= NOW()인 행을 CANCELLED로 전이';

-- -----------------------------------------------------------------------------
-- subscription_payments 인덱스
-- -----------------------------------------------------------------------------

-- [핵심 인덱스 1] 구독별 결제 이력 조회
CREATE INDEX idx_subscription_payments_subscription_id
    ON subscription_payments (subscription_id, billing_at DESC);

COMMENT ON INDEX idx_subscription_payments_subscription_id IS
    '구독별 결제 이력 조회. 구독 상세 조회 시 결제 이력 표시에 활용';

-- [핵심 인덱스 2] 결제 배치 처리 대상 조회
-- 배치: FAILED 상태이면서 재시도 대상인 결제 조회
CREATE INDEX idx_subscription_payments_retry
    ON subscription_payments (billing_at ASC)
    WHERE status = 'FAILED';

COMMENT ON INDEX idx_subscription_payments_retry IS
    '결제 실패 재시도 배치용. status=FAILED 부분 인덱스로 실패 건만 스캔';

-- -----------------------------------------------------------------------------
-- subscription_plans 인덱스
-- -----------------------------------------------------------------------------

-- 상품별 활성 플랜 조회 (상품 상세 조회, 구독 신청 시)
CREATE INDEX idx_subscription_plans_item_id
    ON subscription_plans (item_id)
    WHERE is_active = TRUE;

COMMENT ON INDEX idx_subscription_plans_item_id IS
    '상품별 활성 구독 플랜 조회. 상품 상세 조회 및 구독 신청 API 최적화';

-- -----------------------------------------------------------------------------
-- item_images 인덱스
-- -----------------------------------------------------------------------------

-- 상품별 이미지 목록 조회
CREATE INDEX idx_item_images_item_id
    ON item_images (item_id, sort_order ASC);

COMMENT ON INDEX idx_item_images_item_id IS
    '상품별 이미지 정렬 조회. sort_order 포함하여 ORDER BY 없이 인덱스 정렬 활용';

-- =============================================================================
-- 자동 갱신 트리거 (updated_at)
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION fn_set_updated_at() IS
    'updated_at 컬럼을 현재 시각으로 자동 갱신하는 공통 트리거 함수';

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_items_updated_at
    BEFORE UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_subscription_plans_updated_at
    BEFORE UPDATE ON subscription_plans
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- =============================================================================
-- 테이블 코멘트 보완
-- =============================================================================

COMMENT ON TABLE email_verifications IS
    '이메일 인증 토큰 관리. 인증 완료 또는 만료 후 30일 이후 배치 삭제 대상';

COMMENT ON TABLE password_reset_tokens IS
    '비밀번호 재설정 토큰 관리. 사용 완료(used_at IS NOT NULL) 또는 만료 즉시 배치 삭제 대상';

COMMENT ON TABLE refresh_tokens IS
    '리프레시 토큰 관리. 만료 또는 revoke 후 7일 이후 배치 삭제 대상';

COMMENT ON TABLE subscription_payments IS
    '구독 정기 결제 이력. 전자상거래법 5년 보존. 물리 삭제 금지';

COMMENT ON TABLE orders IS
    '구매 주문 이력. 전자상거래법 5년 보존. 물리 삭제 금지';
