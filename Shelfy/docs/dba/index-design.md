# Shelfy - 인덱스 설계서 (Index Design)

- 작성일: 2026-05-09
- 작성자: DBA
- 버전: v1.0.0
- 대상 DB: PostgreSQL 15+
- 참조 파일: `database/migrations/V1__init_schema.sql`

---

## 목차

1. [설계 원칙](#1-설계-원칙)
2. [쿼리 패턴 분석](#2-쿼리-패턴-분석)
3. [테이블별 인덱스 상세 설계](#3-테이블별-인덱스-상세-설계)
4. [전문 검색 설계 (tsvector + GIN)](#4-전문-검색-설계-tsvector--gin)
5. [파티셔닝 검토](#5-파티셔닝-검토)
6. [인덱스 유지보수 정책](#6-인덱스-유지보수-정책)
7. [모니터링 쿼리](#7-모니터링-쿼리)

---

## 1. 설계 원칙

### 1.1 인덱스 추가 기준

| 기준 | 설명 |
|---|---|
| 선택도 (Selectivity) | 결과 행이 전체의 5% 이하인 컬럼에 인덱스 적용 |
| 조회 빈도 | 단순 INSERT/UPDATE 전용 테이블에는 불필요한 인덱스 지양 |
| 부분 인덱스 우선 | WHERE 조건이 고정된 경우 부분 인덱스(Partial Index)로 크기와 유지비용 절감 |
| 복합 인덱스 컬럼 순서 | 등치 조건(=) 컬럼을 앞에, 범위 조건(>, BETWEEN) 컬럼을 뒤에 배치 |
| EXPLAIN ANALYZE 검증 | 인덱스 추가 전 반드시 실행계획 확인 (Seq Scan → Index Scan 전환 확인) |

### 1.2 PostgreSQL 인덱스 유형 선택 기준

| 유형 | 적용 대상 | Shelfy 적용 예 |
|---|---|---|
| B-Tree | 기본값. 등치, 범위, 정렬 모두 지원 | 대부분의 인덱스 |
| GIN | 배열, JSONB, tsvector 포함 검색 | items.tags (배열), items.search_vector (전문 검색) |
| BRIN | 물리적 순서와 논리적 순서가 일치하는 대용량 append-only 테이블 | subscription_payments (향후 적용 검토) |
| GiST | 지리 데이터, 범위 타입 | 현 시점 미적용 |

---

## 2. 쿼리 패턴 분석

API 요구사항 분석을 통해 도출한 주요 쿼리 패턴이다.

### 2.1 items 테이블 주요 쿼리 패턴

| 패턴 ID | API | 쿼리 조건 | 빈도 |
|---|---|---|---|
| ITEM-Q1 | GET /items | `status = 'PUBLISHED' AND deleted_at IS NULL` + category 필터 + 정렬 | 최고 |
| ITEM-Q2 | GET /items | ITEM-Q1 + `price BETWEEN :min AND :max` | 높음 |
| ITEM-Q3 | GET /items?sort=popular | ITEM-Q1 + `ORDER BY view_count DESC` | 높음 |
| ITEM-Q4 | GET /items/search | `search_vector @@ to_tsquery(...)` + ITEM-Q1 조건 | 높음 |
| ITEM-Q5 | GET /items/my | `seller_id = :id AND deleted_at IS NULL` + status 필터 | 중간 |
| ITEM-Q6 | GET /users/{nickname}/profile | ITEM-Q5 + `status = 'PUBLISHED'` | 중간 |
| ITEM-Q7 | GET /items/{itemId} | `id = :id` (PK 접근) | 최고 |

### 2.2 orders 테이블 주요 쿼리 패턴

| 패턴 ID | API | 쿼리 조건 | 빈도 |
|---|---|---|---|
| ORD-Q1 | GET /orders | `buyer_id = :id ORDER BY created_at DESC` | 높음 |
| ORD-Q2 | GET /orders?startDate=&endDate= | `buyer_id = :id AND paid_at BETWEEN :start AND :end` | 중간 |
| ORD-Q3 | GET /users/me/revenue | `item_id IN (...) AND status = 'COMPLETED' GROUP BY MONTH(paid_at)` | 낮음 |
| ORD-Q4 | 배치: PENDING 정리 | `status = 'PENDING' AND created_at < NOW() - INTERVAL '1 hour'` | 낮음 |

### 2.3 subscriptions 테이블 주요 쿼리 패턴

| 패턴 ID | API | 쿼리 조건 | 빈도 |
|---|---|---|---|
| SUB-Q1 | GET /subscriptions | `subscriber_id = :id ORDER BY created_at DESC` | 높음 |
| SUB-Q2 | POST /subscriptions | `subscriber_id = :id AND item_id = :id AND status IN ('ACTIVE','CANCEL_REQUESTED')` (중복 체크) | 높음 |
| SUB-Q3 | 정기결제 배치 | `status = 'ACTIVE' AND next_billing_at <= NOW()` | 높음 (배치 주기) |
| SUB-Q4 | 해지 만료 배치 | `status = 'CANCEL_REQUESTED' AND active_until <= NOW()` | 중간 |
| SUB-Q5 | GET /users/me/revenue | `item_id IN (...) AND status = 'ACTIVE' COUNT(*)` | 낮음 |

---

## 3. 테이블별 인덱스 상세 설계

### 3.1 users

| 인덱스명 | 컬럼 | 유형 | 조건 (부분) | 근거 및 효과 |
|---|---|---|---|---|
| `pk_users` | id | B-Tree UNIQUE | - | PK. 모든 FK 참조의 기반 |
| `uq_users_email` | email | B-Tree UNIQUE | - | 로그인 조회, 회원가입 중복 체크. 매 로그인마다 수행 |
| `uq_users_nickname` | nickname | B-Tree UNIQUE | - | 닉네임 중복 체크, 프로필 URL 조회 (`/users/{nickname}`) |
| `idx_users_active` | created_at DESC | B-Tree | `deleted_at IS NULL` | 정상 사용자 범위 스캔. 삭제된 계정을 인덱스에서 제외하여 크기 절감 |
| `idx_users_locked` | locked_until | B-Tree | `locked_until IS NOT NULL AND deleted_at IS NULL` | 잠금 계정 배치 해제용. 전체 users 스캔 불필요 |

**트레이드오프**: `email`, `nickname`은 UNIQUE 제약조건이므로 인덱스 자동 생성. 별도 인덱스 불필요.

---

### 3.2 items

#### 핵심 인덱스 설명

**idx_items_browse_category_latest**

```sql
CREATE INDEX idx_items_browse_category_latest
    ON items (category, created_at DESC)
    WHERE status = 'PUBLISHED' AND deleted_at IS NULL;
```

- 대상 쿼리: `GET /items?category=TEMPLATE&sort=latest`
- 효과: `status`, `deleted_at` 조건을 부분 인덱스로 처리하여 전체 items가 아닌 공개 상품만 인덱싱. 약 70-80% 행 제외 예상 (DRAFT, 삭제 상품)
- 정렬: `created_at DESC` 포함으로 ORDER BY 추가 정렬 작업 없이 Index Scan만으로 정렬 완료

**idx_items_browse_price**

```sql
CREATE INDEX idx_items_browse_price
    ON items (price ASC, created_at DESC)
    WHERE status = 'PUBLISHED' AND deleted_at IS NULL AND price IS NOT NULL;
```

- 대상 쿼리: `GET /items?minPrice=5000&maxPrice=30000&sort=lowPrice`
- 효과: 가격 범위 필터(`price BETWEEN :min AND :max`) + 가격순 정렬을 단일 인덱스 스캔으로 처리
- SUBSCRIBE 전용 상품(price IS NULL)을 부분 인덱스에서 제외

**idx_items_browse_popular**

```sql
CREATE INDEX idx_items_browse_popular
    ON items (view_count DESC, created_at DESC)
    WHERE status = 'PUBLISHED' AND deleted_at IS NULL;
```

- 대상 쿼리: `GET /items?sort=popular`
- 주의: `view_count`는 빈번한 UPDATE 대상. 인덱스 유지 비용 발생. 비동기 배치 갱신 권장 (Redis 버퍼 → 배치 DB 반영)

**idx_items_search_vector (GIN)**

```sql
CREATE INDEX idx_items_search_vector
    ON items USING GIN (search_vector);
```

- 대상 쿼리: `GET /items/search?q=포토샵`
- `search_vector`는 INSERT/UPDATE 트리거로 자동 갱신 (`title 가중치A + description 가중치B + tags 가중치C`)
- GIN 인덱스는 B-Tree보다 빌드 시간이 길지만 포함 검색 성능이 월등히 우수

**idx_items_tags (GIN)**

```sql
CREATE INDEX idx_items_tags
    ON items USING GIN (tags);
```

- 대상 쿼리: `WHERE tags @> ARRAY['포토샵']` (태그 포함 검색)
- 배열 포함 연산자(`@>`)는 GIN 인덱스 없이는 Seq Scan 발생

| 인덱스명 | 컬럼 | 유형 | 조건 (부분) | 대상 쿼리 패턴 |
|---|---|---|---|---|
| `pk_items` | id | B-Tree UNIQUE | - | PK 직접 조회 (ITEM-Q7) |
| `idx_items_browse_category_latest` | (category, created_at DESC) | B-Tree | PUBLISHED, 미삭제 | ITEM-Q1 |
| `idx_items_browse_price` | (price ASC, created_at DESC) | B-Tree | PUBLISHED, 미삭제, price IS NOT NULL | ITEM-Q2 |
| `idx_items_browse_popular` | (view_count DESC, created_at DESC) | B-Tree | PUBLISHED, 미삭제 | ITEM-Q3 |
| `idx_items_search_vector` | search_vector | GIN | - | ITEM-Q4 (전문 검색) |
| `idx_items_tags` | tags | GIN | - | 태그 포함 검색 |
| `idx_items_sale_type` | (sale_type, created_at DESC) | B-Tree | PUBLISHED, 미삭제 | saleType 필터 |
| `idx_items_seller_id` | (seller_id, created_at DESC) | B-Tree | 미삭제 | ITEM-Q5, ITEM-Q6 |

**트레이드오프 요약**:
- 부분 인덱스 5개로 실제 인덱스 크기는 전체 행 대비 약 60-70% 수준 예상
- `view_count` 갱신 빈도가 높아질 경우 `idx_items_browse_popular` 유지 비용 재검토 필요
- 복합 필터(category + saleType + priceRange + sort) 조합은 Planner가 가장 선택도가 높은 인덱스를 선택. 쿼리 패턴 다양화 시 `pg_stat_statements`로 슬로우 쿼리 재분석

---

### 3.3 orders

| 인덱스명 | 컬럼 | 유형 | 조건 (부분) | 대상 쿼리 패턴 |
|---|---|---|---|---|
| `pk_orders` | id | B-Tree UNIQUE | - | PK 직접 조회 |
| `uq_orders_pg_transaction_id` | pg_transaction_id | B-Tree UNIQUE | - | PG사 결제 완료 콜백 중복 처리 방지 |
| `idx_orders_buyer_id` | (buyer_id, created_at DESC) | B-Tree | - | ORD-Q1 (구매 내역 목록) |
| `idx_orders_buyer_paid_at` | (buyer_id, paid_at DESC) | B-Tree | paid_at IS NOT NULL | ORD-Q2 (날짜 범위 조회) |
| `idx_orders_item_id` | (item_id, status, paid_at DESC) | B-Tree | - | ORD-Q3 (셀러 수익 집계) |
| `idx_orders_pending` | created_at DESC | B-Tree | status = 'PENDING' | ORD-Q4 (PENDING 정리 배치) |

**설계 결정**:
- `buyer_id` 단독 인덱스 대신 `(buyer_id, created_at DESC)` 복합 인덱스로 ORDER BY 비용 제거
- `pg_transaction_id`의 UNIQUE 제약조건은 이중 결제 처리 방지를 위한 DB 레벨 가드

---

### 3.4 subscriptions

| 인덱스명 | 컬럼 | 유형 | 조건 (부분) | 대상 쿼리 패턴 |
|---|---|---|---|---|
| `pk_subscriptions` | id | B-Tree UNIQUE | - | PK 직접 조회 |
| `uq_subscriptions_active_per_user_item` | (subscriber_id, item_id) | B-Tree UNIQUE | status IN ('ACTIVE', 'CANCEL_REQUESTED') | SUB-Q2 (중복 구독 방지, 정합성 보장) |
| `idx_subscriptions_subscriber_id` | (subscriber_id, created_at DESC) | B-Tree | - | SUB-Q1 (구독 이력 목록) |
| `idx_subscriptions_subscriber_active` | (subscriber_id, item_id) | B-Tree | status IN ('ACTIVE', 'CANCEL_REQUESTED') | SUB-Q2 (조회 최적화) |
| `idx_subscriptions_billing_batch` | next_billing_at ASC | B-Tree | status = 'ACTIVE' | SUB-Q3 (정기결제 배치) |
| `idx_subscriptions_item_id_status` | (item_id, status) | B-Tree | - | SUB-Q5 (상품별 구독자 집계) |
| `idx_subscriptions_cancel_expiry` | active_until ASC | B-Tree | status = 'CANCEL_REQUESTED' | SUB-Q4 (해지 만료 배치) |

**핵심 설계 포인트 - uq_subscriptions_active_per_user_item**:

```sql
CREATE UNIQUE INDEX uq_subscriptions_active_per_user_item
    ON subscriptions (subscriber_id, item_id)
    WHERE status IN ('ACTIVE', 'CANCEL_REQUESTED');
```

- 이 부분 UNIQUE 인덱스는 단순 성능 최적화가 아닌 **데이터 정합성 보장** 목적
- 애플리케이션 레이어에서 중복 구독 체크를 수행하더라도, 동시 요청(Race Condition) 상황에서 DB 레벨 제약이 없으면 중복 구독이 삽입될 수 있음
- `CANCELLED` 상태의 구독 이력은 부분 인덱스에서 제외되어 재구독 허용

---

### 3.5 subscription_payments

| 인덱스명 | 컬럼 | 유형 | 조건 (부분) | 대상 쿼리 패턴 |
|---|---|---|---|---|
| `pk_subscription_payments` | id | B-Tree UNIQUE | - | PK 직접 조회 |
| `uq_subscription_payments_pg_transaction_id` | pg_transaction_id | B-Tree UNIQUE | - | 이중 결제 방지 |
| `idx_subscription_payments_subscription_id` | (subscription_id, billing_at DESC) | B-Tree | - | 구독별 결제 이력 조회 |
| `idx_subscription_payments_retry` | billing_at ASC | B-Tree | status = 'FAILED' | 결제 실패 재시도 배치 |

---

### 3.6 subscription_plans

| 인덱스명 | 컬럼 | 유형 | 조건 (부분) | 대상 쿼리 패턴 |
|---|---|---|---|---|
| `pk_subscription_plans` | id | B-Tree UNIQUE | - | PK 직접 조회 |
| `uq_subscription_plans_item_period_name` | (item_id, period, plan_name) | B-Tree UNIQUE | - | 동일 상품 내 중복 플랜 방지 |
| `idx_subscription_plans_item_id` | item_id | B-Tree | is_active = TRUE | 상품 상세 조회 시 활성 플랜 목록 |

---

### 3.7 item_images

| 인덱스명 | 컬럼 | 유형 | 조건 (부분) | 대상 쿼리 패턴 |
|---|---|---|---|---|
| `pk_item_images` | id | B-Tree UNIQUE | - | PK 직접 조회 |
| `uq_item_images_sort_order` | (item_id, sort_order) | B-Tree UNIQUE | - | 이미지 순서 중복 방지 |
| `uq_item_images_thumbnail` | item_id | B-Tree UNIQUE | is_thumbnail = TRUE | 대표 이미지 1개 보장 |
| `idx_item_images_item_id` | (item_id, sort_order ASC) | B-Tree | - | 상품별 이미지 순서 조회 |

---

## 4. 전문 검색 설계 (tsvector + GIN)

### 4.1 설계 구조

```
items.search_vector (TSVECTOR)
├── title      → 가중치 A (최고 우선순위, 검색 랭킹에서 가장 높은 점수)
├── description → 가중치 B
└── tags        → 가중치 C (배열을 공백 구분 문자열로 변환 후 벡터화)
```

### 4.2 트리거 갱신 방식 선택 이유

| 방식 | 장점 | 단점 | 선택 여부 |
|---|---|---|---|
| 트리거 자동 갱신 | 항상 최신 상태 유지, 애플리케이션 코드 불필요 | INSERT/UPDATE마다 추가 연산 | **선택** |
| 애플리케이션에서 직접 설정 | 유연한 제어 가능 | 코드 누락 시 데이터 불일치 위험 | 미선택 |
| 배치 갱신 | 쓰기 부하 분리 | 검색 지연(Lag) 발생 | 미선택 |

트리거 방식을 선택한 주요 이유:
- 상품 수정 API(PUT /items)에서 title/description/tags 변경 시 자동 반영 보장
- ORM(MyBatis/JPA) 레이어에서 search_vector를 직접 다루지 않아도 됨

### 4.3 검색 쿼리 패턴

```sql
-- 기본 전문 검색 (가중치 랭킹 포함)
SELECT id, title,
       ts_rank(search_vector, query) AS rank
FROM items,
     to_tsquery('simple', '포토샵 & 템플릿') AS query
WHERE search_vector @@ query
  AND status = 'PUBLISHED'
  AND deleted_at IS NULL
ORDER BY rank DESC, created_at DESC
LIMIT 20 OFFSET 0;

-- 단일 키워드 (공백 포함 한글 키워드)
SELECT id, title
FROM items
WHERE search_vector @@ to_tsquery('simple', '포토샵:*')
  AND status = 'PUBLISHED'
  AND deleted_at IS NULL;
```

### 4.4 한국어 전문 검색 한계 및 개선 방안

| 구분 | 현재 (PostgreSQL simple) | 개선 방안 |
|---|---|---|
| 형태소 분석 | 미지원 (어절 단위 분리) | pg_bigm 설치 또는 Elasticsearch 연동 |
| 부분 일치 | `:*` 접두어 매칭만 가능 | pg_trgm GIN 인덱스 보조 (LIKE '%키워드%') |
| 동의어/유사어 | 미지원 | 사전(Dictionary) 파일 커스터마이징 |
| 초성 검색 | 미지원 | 애플리케이션 레이어 전처리 필요 |

**단기 보완책**: `pg_trgm` 익스텐션의 `similarity()` 함수 및 GIN 인덱스를 tsvector와 병행 적용하여 LIKE 검색 성능 확보

```sql
-- pg_trgm을 활용한 유사 검색 보조
CREATE INDEX idx_items_title_trgm
    ON items USING GIN (title gin_trgm_ops)
    WHERE status = 'PUBLISHED' AND deleted_at IS NULL;

-- 활용 예
SELECT id, title FROM items
WHERE title ILIKE '%포토%'
  AND status = 'PUBLISHED'
  AND deleted_at IS NULL;
```

---

## 5. 파티셔닝 검토

### 5.1 현재 결론: 파티셔닝 불필요

서비스 초기 단계에서 파티셔닝 도입은 운영 복잡도 증가 대비 효과가 미미하다. 아래 기준을 초과할 때 도입을 재검토한다.

| 테이블 | 파티셔닝 검토 기준 | 현재 판단 |
|---|---|---|
| `subscription_payments` | 연간 결제 건수 100만 건 초과 | 현 시점 불필요 |
| `orders` | 누적 주문 500만 건 초과 | 현 시점 불필요 |
| `items` | 등록 상품 100만 건 초과 | 현 시점 불필요 |

### 5.2 향후 파티셔닝 설계안 (subscription_payments)

도입 기준 충족 시 `created_at` 기준 연간 Range 파티셔닝 적용.

```sql
-- 파티셔닝 전환 예시 (마이그레이션 필요)
CREATE TABLE subscription_payments (
    ...
) PARTITION BY RANGE (created_at);

CREATE TABLE subscription_payments_2026
    PARTITION OF subscription_payments
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE TABLE subscription_payments_2027
    PARTITION OF subscription_payments
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');
```

**주의**: 파티셔닝 전환은 대규모 데이터 마이그레이션을 동반하므로 반드시 무중단 마이그레이션 계획 수립 후 진행.

---

## 6. 인덱스 유지보수 정책

### 6.1 VACUUM / AUTOVACUUM

`items` 테이블의 `view_count`는 빈번한 UPDATE로 인한 데드 튜플(Dead Tuple) 누적 위험이 있다. 아래 파라미터로 autovacuum 민감도를 높인다.

```sql
-- items 테이블 autovacuum 민감도 조정
ALTER TABLE items SET (
    autovacuum_vacuum_scale_factor = 0.01,   -- 기본값 0.2 → 변경 행 1% 초과 시 즉시 vacuum
    autovacuum_analyze_scale_factor = 0.005  -- 기본값 0.1 → 0.5% 초과 시 analyze
);
```

### 6.2 인덱스 재빌드 기준

| 조건 | 조치 |
|---|---|
| `pg_stat_user_indexes.idx_blks_hit / idx_blks_read` 비율이 낮을 때 | `REINDEX INDEX CONCURRENTLY` |
| 대량 삭제/업데이트 후 인덱스 bloat 발생 시 | `REINDEX INDEX CONCURRENTLY` (무중단) |
| `pg_stat_user_indexes.idx_scan = 0` 인 인덱스 | 사용되지 않는 인덱스 → 제거 검토 |

```sql
-- 사용되지 않는 인덱스 확인
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexname NOT LIKE 'pk_%'
  AND indexname NOT LIKE 'uq_%'
ORDER BY tablename;
```

### 6.3 인덱스 Bloat 확인

```sql
-- 인덱스 bloat 확인 (pgstattuple 익스텐션 필요)
SELECT indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
       idx_scan,
       idx_tup_read,
       idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

## 7. 모니터링 쿼리

### 7.1 슬로우 쿼리 식별 (pg_stat_statements)

```sql
-- 평균 실행 시간 상위 20 쿼리
SELECT substring(query, 1, 100) AS query_preview,
       calls,
       round(mean_exec_time::numeric, 2)  AS avg_ms,
       round(total_exec_time::numeric, 2) AS total_ms,
       rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### 7.2 Lock 모니터링

```sql
-- 현재 Lock 대기 상황
SELECT
    blocked.pid                         AS blocked_pid,
    blocked.query                       AS blocked_query,
    blocking.pid                        AS blocking_pid,
    blocking.query                      AS blocking_query,
    now() - blocked.query_start         AS wait_duration
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked
    ON blocked.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.granted
    AND NOT blocked_locks.granted
JOIN pg_catalog.pg_stat_activity blocking
    ON blocking.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted
ORDER BY wait_duration DESC;
```

### 7.3 인덱스 히트율 확인

```sql
-- 테이블별 인덱스 히트율 (99% 이상 유지 목표)
SELECT relname                                                       AS table_name,
       round(100.0 * idx_scan / NULLIF(seq_scan + idx_scan, 0), 2) AS idx_hit_rate,
       seq_scan,
       idx_scan
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY seq_scan DESC;
```

### 7.4 정기결제 배치 대상 확인

```sql
-- 정기결제 배치 대상 건수 확인 (배치 실행 전 사전 점검)
SELECT COUNT(*) AS billing_target_count
FROM subscriptions
WHERE status = 'ACTIVE'
  AND next_billing_at <= NOW();
```

### 7.5 table bloat 확인

```sql
-- 테이블별 dead tuple 비율
SELECT relname,
       n_dead_tup,
       n_live_tup,
       round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
       last_vacuum,
       last_autovacuum
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY dead_pct DESC NULLS LAST;
```

---

## 부록. 인덱스 목록 요약

| 테이블 | 인덱스명 | 컬럼 | 유형 | 부분 조건 | 목적 |
|---|---|---|---|---|---|
| users | pk_users | id | UNIQUE | - | PK |
| users | uq_users_email | email | UNIQUE | - | 로그인, 중복 체크 |
| users | uq_users_nickname | nickname | UNIQUE | - | 프로필 URL, 중복 체크 |
| users | idx_users_active | created_at DESC | B-Tree | deleted_at IS NULL | 정상 사용자 조회 |
| users | idx_users_locked | locked_until | B-Tree | locked_until IS NOT NULL | 잠금 배치 |
| email_verifications | idx_email_verifications_user_id | (user_id, created_at DESC) | B-Tree | - | 최신 토큰 조회 |
| email_verifications | idx_email_verifications_cleanup | expires_at | B-Tree | verified_at IS NULL | 만료 토큰 배치 삭제 |
| refresh_tokens | uq_refresh_tokens_token_hash | token_hash | UNIQUE | - | 토큰 검증 |
| refresh_tokens | idx_refresh_tokens_user_id_active | (user_id, expires_at DESC) | B-Tree | revoked_at IS NULL | 유효 토큰 조회 |
| refresh_tokens | idx_refresh_tokens_cleanup | expires_at | B-Tree | revoked_at IS NULL | 만료 토큰 배치 |
| items | pk_items | id | UNIQUE | - | PK |
| items | idx_items_browse_category_latest | (category, created_at DESC) | B-Tree | PUBLISHED+미삭제 | 카테고리 탐색 |
| items | idx_items_browse_price | (price ASC, created_at DESC) | B-Tree | PUBLISHED+미삭제+price IS NOT NULL | 가격 필터 |
| items | idx_items_browse_popular | (view_count DESC, created_at DESC) | B-Tree | PUBLISHED+미삭제 | 인기순 정렬 |
| items | idx_items_search_vector | search_vector | GIN | - | 전문 검색 |
| items | idx_items_tags | tags | GIN | - | 태그 포함 검색 |
| items | idx_items_sale_type | (sale_type, created_at DESC) | B-Tree | PUBLISHED+미삭제 | 판매유형 필터 |
| items | idx_items_seller_id | (seller_id, created_at DESC) | B-Tree | 미삭제 | 셀러 상품 목록 |
| item_images | uq_item_images_sort_order | (item_id, sort_order) | UNIQUE | - | 순서 중복 방지 |
| item_images | uq_item_images_thumbnail | item_id | UNIQUE | is_thumbnail=TRUE | 대표이미지 1개 보장 |
| item_images | idx_item_images_item_id | (item_id, sort_order ASC) | B-Tree | - | 이미지 순서 조회 |
| subscription_plans | uq_subscription_plans_item_period_name | (item_id, period, plan_name) | UNIQUE | - | 중복 플랜 방지 |
| subscription_plans | idx_subscription_plans_item_id | item_id | B-Tree | is_active=TRUE | 활성 플랜 조회 |
| orders | pk_orders | id | UNIQUE | - | PK |
| orders | uq_orders_pg_transaction_id | pg_transaction_id | UNIQUE | - | 이중결제 방지 |
| orders | idx_orders_buyer_id | (buyer_id, created_at DESC) | B-Tree | - | 구매 내역 조회 |
| orders | idx_orders_buyer_paid_at | (buyer_id, paid_at DESC) | B-Tree | paid_at IS NOT NULL | 날짜 범위 조회 |
| orders | idx_orders_item_id | (item_id, status, paid_at DESC) | B-Tree | - | 수익 집계 |
| orders | idx_orders_pending | created_at DESC | B-Tree | status='PENDING' | PENDING 배치 |
| subscriptions | pk_subscriptions | id | UNIQUE | - | PK |
| subscriptions | uq_subscriptions_active_per_user_item | (subscriber_id, item_id) | UNIQUE | ACTIVE+CANCEL_REQUESTED | 중복 구독 방지 (정합성) |
| subscriptions | idx_subscriptions_subscriber_id | (subscriber_id, created_at DESC) | B-Tree | - | 구독 이력 조회 |
| subscriptions | idx_subscriptions_subscriber_active | (subscriber_id, item_id) | B-Tree | ACTIVE+CANCEL_REQUESTED | 활성 구독 조회 |
| subscriptions | idx_subscriptions_billing_batch | next_billing_at ASC | B-Tree | status='ACTIVE' | 정기결제 배치 |
| subscriptions | idx_subscriptions_item_id_status | (item_id, status) | B-Tree | - | 상품별 구독자 집계 |
| subscriptions | idx_subscriptions_cancel_expiry | active_until ASC | B-Tree | status='CANCEL_REQUESTED' | 해지 만료 배치 |
| subscription_payments | pk_subscription_payments | id | UNIQUE | - | PK |
| subscription_payments | uq_subscription_payments_pg_transaction_id | pg_transaction_id | UNIQUE | - | 이중결제 방지 |
| subscription_payments | idx_subscription_payments_subscription_id | (subscription_id, billing_at DESC) | B-Tree | - | 결제 이력 조회 |
| subscription_payments | idx_subscription_payments_retry | billing_at ASC | B-Tree | status='FAILED' | 실패 재시도 배치 |
