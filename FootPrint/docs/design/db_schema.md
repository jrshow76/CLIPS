# 데이터베이스 설계 문서

- **프로젝트명**: 발자국 (Foot-Print)
- **문서 버전**: v1.0.0
- **작성일**: 2026-05-09
- **작성자**: DBA
- **DB 엔진**: PostgreSQL 16

---

## 목차

1. [ERD (텍스트 기반)](#1-erd-텍스트-기반)
2. [테이블 정의](#2-테이블-정의)
   - [users](#21-users-사용자)
   - [categories](#22-categories-카테고리)
   - [places](#23-places-장소)
   - [place_category](#24-place_category-장소-카테고리-매핑)
   - [place_photos](#25-place_photos-장소-사진)
   - [place_tags](#26-place_tags-장소-태그)
   - [refresh_tokens](#27-refresh_tokens-리프레시-토큰)
3. [인덱스 설계](#3-인덱스-설계)
4. [파티셔닝 전략](#4-파티셔닝-전략)
5. [VACUUM / Autovacuum 설정 권고사항](#5-vacuum--autovacuum-설정-권고사항)
6. [설계 결정 사항 및 근거](#6-설계-결정-사항-및-근거)

---

## 1. ERD (텍스트 기반)

```
┌─────────────────────┐
│        users        │
│─────────────────────│
│ id (PK, UUID)       │
│ email               │
│ password_hash       │
│ nickname            │
│ profile_image_url   │
│ created_at          │
│ updated_at          │
│ deleted_at          │
└──────────┬──────────┘
           │ 1
           │
           │ N
┌──────────▼──────────┐        ┌───────────────────────┐
│      categories     │        │       place_tags        │
│─────────────────────│        │───────────────────────  │
│ id (PK, BIGSERIAL)  │        │ id (PK, BIGSERIAL)      │
│ user_id (FK, NULL)  │        │ place_id (FK)           │
│ name                │        │ tag                     │
│ color               │        │ created_at              │
│ icon                │        └───────────┬─────────────┘
│ is_default          │                    │ N
│ sort_order          │                    │
│ created_at          │                    │ 1
│ updated_at          │        ┌───────────▼─────────────┐
└──────────┬──────────┘        │          places          │
           │ N                 │─────────────────────────│
           │                   │ id (PK, BIGSERIAL)       │
┌──────────▼──────────┐        │ user_id (FK)             │
│   place_category    │        │ name                     │
│─────────────────────│        │ address                  │
│ place_id (FK, PK)   ├────────┤ latitude                 │
│ category_id (FK,PK) │        │ longitude                │
└─────────────────────┘        │ visited_at               │
                                │ memo                     │
                                │ rating                   │
                                │ created_at               │
                                │ updated_at               │
                                │ deleted_at               │
                                └───────────┬──────────────┘
                                            │ 1
                                            │
                                            │ N
                                ┌───────────▼──────────────┐
                                │       place_photos        │
                                │──────────────────────────│
                                │ id (PK, BIGSERIAL)        │
                                │ place_id (FK)             │
                                │ file_name                 │
                                │ original_name             │
                                │ file_url                  │
                                │ thumbnail_url             │
                                │ file_size                 │
                                │ mime_type                 │
                                │ sort_order                │
                                │ created_at                │
                                └───────────────────────────┘

┌──────────────────────────┐
│      refresh_tokens       │
│──────────────────────────│
│ id (PK, BIGSERIAL)        │
│ user_id (FK)              │
│ token_hash                │
│ expires_at                │
│ created_at                │
│ revoked_at                │
└───────────────────────────┘
```

**관계 요약**

| 관계 | 카디널리티 | 설명 |
|------|-----------|------|
| users - places | 1:N | 사용자 1명은 장소를 여러 개 등록 가능 |
| users - categories | 1:N | 사용자 1명은 커스텀 카테고리를 여러 개 생성 가능 |
| users - refresh_tokens | 1:N | 사용자 1명은 여러 디바이스에서 토큰 보유 가능 |
| places - categories | N:M | 장소 1개는 여러 카테고리에 속할 수 있고, 카테고리 1개에는 여러 장소 포함 |
| places - place_photos | 1:N | 장소 1개당 최대 5장 사진 등록 |
| places - place_tags | 1:N | 장소 1개당 최대 10개 태그 등록 |

---

## 2. 테이블 정의

### 2.1 users (사용자)

> 서비스의 기본 회원 정보를 저장한다.
> userId는 UUID 타입을 사용하여 순차 ID 노출로 인한 보안 취약점을 방지한다.

| 컬럼명 | 타입 | NOT NULL | 기본값 | 설명 |
|--------|------|----------|--------|------|
| id | UUID | Y | gen_random_uuid() | PK, 사용자 고유 식별자 |
| email | VARCHAR(255) | Y | - | 이메일 (UNIQUE, 로그인 ID) |
| password_hash | VARCHAR(255) | Y | - | bcrypt 해시 비밀번호 (cost factor 10 이상) |
| nickname | VARCHAR(20) | Y | - | 닉네임 (2~20자) |
| profile_image_url | TEXT | N | NULL | 프로필 이미지 URL (CDN 경로) |
| created_at | TIMESTAMPTZ | Y | NOW() | 생성일시 |
| updated_at | TIMESTAMPTZ | Y | NOW() | 최종 수정일시 |
| deleted_at | TIMESTAMPTZ | N | NULL | 탈퇴일시 (NULL = 정상 계정, Soft Delete) |

**제약조건**
- `email` UNIQUE 제약 (논리 삭제 고려: `deleted_at IS NULL` 부분 인덱스로 유니크 보장)
- `nickname` 길이 CHECK: `char_length(nickname) BETWEEN 2 AND 20`
- `email` 길이 CHECK: `char_length(email) <= 255`

---

### 2.2 categories (카테고리)

> 시스템 기본 카테고리(is_default=true, user_id=NULL)와 사용자 정의 카테고리(user_id=해당 사용자)를 동일 테이블에 관리한다.
> 기본 카테고리는 모든 사용자가 공유하며, 수정/삭제가 불가하다.

| 컬럼명 | 타입 | NOT NULL | 기본값 | 설명 |
|--------|------|----------|--------|------|
| id | BIGSERIAL | Y | - | PK, 카테고리 고유 식별자 |
| user_id | UUID | N | NULL | FK → users.id (NULL = 시스템 기본 카테고리) |
| name | VARCHAR(20) | Y | - | 카테고리명 (1~20자) |
| color | VARCHAR(7) | Y | '#94A3B8' | HEX 색상 코드 (#RRGGBB) |
| icon | VARCHAR(50) | Y | 'default' | 아이콘 코드 |
| is_default | BOOLEAN | Y | FALSE | TRUE = 시스템 기본 카테고리 |
| sort_order | SMALLINT | Y | 999 | 목록 정렬 순서 |
| created_at | TIMESTAMPTZ | Y | NOW() | 생성일시 |
| updated_at | TIMESTAMPTZ | Y | NOW() | 최종 수정일시 |

**제약조건**
- `color` CHECK: `color ~ '^#[0-9A-Fa-f]{6}$'`
- 사용자별 카테고리명 중복 방지: (user_id, name) UNIQUE (NULL 제외)
- 기본 카테고리명 중복 방지: (is_default, name) 부분 UNIQUE (is_default=true 조건)
- 사용자당 최대 20개 제약: 애플리케이션 계층에서 처리 (DB 트리거 방식은 Lock 부담으로 제외)

---

### 2.3 places (장소)

> 사용자가 방문·기록한 장소의 핵심 정보를 저장한다.
> 소프트 딜리트(deleted_at)를 적용하여 데이터 복구 가능성을 확보한다.
> 태그는 place_tags 테이블에 분리 저장하여 검색 효율을 높인다.

| 컬럼명 | 타입 | NOT NULL | 기본값 | 설명 |
|--------|------|----------|--------|------|
| id | BIGSERIAL | Y | - | PK, 장소 고유 식별자 |
| user_id | UUID | Y | - | FK → users.id (장소 소유자) |
| name | VARCHAR(100) | Y | - | 장소명 (1~100자) |
| address | VARCHAR(255) | N | NULL | 주소 (지도 API 자동 입력 또는 직접 입력) |
| latitude | NUMERIC(10,8) | Y | - | 위도 (-90.0 ~ 90.0, 소수점 8자리) |
| longitude | NUMERIC(11,8) | Y | - | 경도 (-180.0 ~ 180.0, 소수점 8자리) |
| visited_at | DATE | Y | - | 방문일 (미래 날짜 불가) |
| memo | TEXT | N | NULL | 메모 (최대 2,000자, 애플리케이션 계층 제한) |
| rating | SMALLINT | N | NULL | 평점 (1~5 정수, NULL = 미입력) |
| created_at | TIMESTAMPTZ | Y | NOW() | 생성일시 |
| updated_at | TIMESTAMPTZ | Y | NOW() | 최종 수정일시 |
| deleted_at | TIMESTAMPTZ | N | NULL | 삭제일시 (NULL = 미삭제, Soft Delete) |

**제약조건**
- `latitude` CHECK: `latitude BETWEEN -90.0 AND 90.0`
- `longitude` CHECK: `longitude BETWEEN -180.0 AND 180.0`
- `rating` CHECK: `rating IS NULL OR rating BETWEEN 1 AND 5`
- `visited_at` CHECK: `visited_at <= CURRENT_DATE` (애플리케이션 계층에서 1차 검증)
- `name` 길이 CHECK: `char_length(name) BETWEEN 1 AND 100`

---

### 2.4 place_category (장소-카테고리 매핑)

> places와 categories의 N:M 관계를 표현하는 연결 테이블이다.
> 하나의 장소는 1개 이상의 카테고리에 속할 수 있다.

| 컬럼명 | 타입 | NOT NULL | 기본값 | 설명 |
|--------|------|----------|--------|------|
| place_id | BIGINT | Y | - | FK → places.id |
| category_id | BIGINT | Y | - | FK → categories.id |

**제약조건**
- PRIMARY KEY (place_id, category_id) — 복합 PK
- ON DELETE CASCADE: 장소 삭제 시 매핑 자동 삭제
- ON DELETE RESTRICT: 카테고리 삭제 시 매핑 존재하면 오류 (애플리케이션에서 CATEGORY_IN_USE 처리)

---

### 2.5 place_photos (장소 사진)

> 장소에 첨부된 사진 메타데이터를 저장한다.
> 실제 파일은 CDN/Object Storage에 저장되며, 이 테이블은 URL과 순서만 관리한다.
> 장소당 최대 5장 제약은 애플리케이션 계층에서 처리한다.

| 컬럼명 | 타입 | NOT NULL | 기본값 | 설명 |
|--------|------|----------|--------|------|
| id | BIGSERIAL | Y | - | PK, 사진 고유 식별자 |
| place_id | BIGINT | Y | - | FK → places.id |
| file_name | VARCHAR(255) | Y | - | 서버 재생성 파일명 (보안용 UUID 기반) |
| original_name | VARCHAR(255) | Y | - | 원본 파일명 |
| file_url | TEXT | Y | - | 원본 이미지 URL (CDN) |
| thumbnail_url | TEXT | N | NULL | 썸네일 이미지 URL (CDN, 리사이즈 후 생성) |
| file_size | INTEGER | Y | - | 파일 크기 (bytes) |
| mime_type | VARCHAR(50) | Y | - | MIME 타입 (image/jpeg, image/png, image/webp) |
| sort_order | SMALLINT | Y | 1 | 사진 정렬 순서 (1~5) |
| created_at | TIMESTAMPTZ | Y | NOW() | 업로드 일시 |

**제약조건**
- `sort_order` CHECK: `sort_order BETWEEN 1 AND 5`
- `mime_type` CHECK: `mime_type IN ('image/jpeg', 'image/png', 'image/webp')`
- `file_size` CHECK: `file_size > 0 AND file_size <= 10485760` (10MB)

---

### 2.6 place_tags (장소 태그)

> 장소에 부여된 태그를 정규화하여 저장한다.
> 태그 별도 테이블 분리로 키워드 검색 시 GIN 인덱스 활용이 가능하다.
> 장소당 최대 10개, 태그당 최대 20자 제약은 애플리케이션 계층에서 처리한다.

| 컬럼명 | 타입 | NOT NULL | 기본값 | 설명 |
|--------|------|----------|--------|------|
| id | BIGSERIAL | Y | - | PK |
| place_id | BIGINT | Y | - | FK → places.id |
| tag | VARCHAR(20) | Y | - | 태그 값 (1~20자) |
| created_at | TIMESTAMPTZ | Y | NOW() | 생성일시 |

**제약조건**
- (place_id, tag) UNIQUE — 동일 장소에 중복 태그 방지
- `tag` 길이 CHECK: `char_length(tag) BETWEEN 1 AND 20`
- ON DELETE CASCADE: 장소 삭제 시 태그 자동 삭제

---

### 2.7 refresh_tokens (리프레시 토큰)

> JWT Refresh Token의 서버 측 레코드를 관리한다.
> 실제 토큰 값 대신 해시값을 저장하여 DB 탈취 시 토큰 재사용을 방지한다.
> 만료(revoked_at, expires_at)된 레코드는 주기적으로 정리(Batch/Cron)한다.

| 컬럼명 | 타입 | NOT NULL | 기본값 | 설명 |
|--------|------|----------|--------|------|
| id | BIGSERIAL | Y | - | PK |
| user_id | UUID | Y | - | FK → users.id |
| token_hash | VARCHAR(255) | Y | - | SHA-256 해시된 토큰 (UNIQUE) |
| expires_at | TIMESTAMPTZ | Y | - | 토큰 만료일시 (발급 시 +7일) |
| created_at | TIMESTAMPTZ | Y | NOW() | 발급 일시 |
| revoked_at | TIMESTAMPTZ | N | NULL | 무효화 일시 (NULL = 유효, 로그아웃 시 설정) |

**제약조건**
- `token_hash` UNIQUE
- `expires_at` CHECK: `expires_at > created_at`

---

## 3. 인덱스 설계

### 3.1 설계 원칙

- 인덱스 추가 전 반드시 `EXPLAIN ANALYZE`로 실행계획을 확인한다.
- 쓰기 빈도가 높은 테이블(`places`, `place_photos`)은 인덱스 수를 최소화한다.
- `deleted_at IS NULL` 조건이 포함된 쿼리에는 부분 인덱스(Partial Index)를 사용하여 인덱스 크기를 줄인다.
- 복합 인덱스는 선택도(Selectivity)가 높은 컬럼을 앞에 배치한다.

### 3.2 인덱스 목록

#### users 테이블

| 인덱스명 | 유형 | 대상 컬럼 | 조건 | 근거 API |
|---------|------|----------|------|---------|
| idx_users_email_active | B-Tree (UNIQUE) | email | WHERE deleted_at IS NULL | A-01(회원가입 이메일 중복 확인), A-02(로그인 인증) |

```
-- 이메일 로그인 시 매번 실행되는 쿼리:
-- SELECT * FROM users WHERE email = $1 AND deleted_at IS NULL
-- deleted_at IS NULL 조건의 부분 인덱스로 논리 삭제된 계정 제외,
-- 인덱스 크기 최소화 및 스캔 성능 향상
```

#### categories 테이블

| 인덱스명 | 유형 | 대상 컬럼 | 조건 | 근거 API |
|---------|------|----------|------|---------|
| idx_categories_user_id | B-Tree | user_id | - | C-01(카테고리 목록 조회) |
| uq_categories_user_name | B-Tree (UNIQUE) | (user_id, name) | WHERE user_id IS NOT NULL | C-02(사용자 카테고리명 중복 방지) |

```
-- C-01 카테고리 목록 조회 쿼리:
-- SELECT * FROM categories WHERE user_id = $1 OR is_default = true ORDER BY sort_order
-- user_id 단일 인덱스로 사용자 카테고리를 빠르게 조회
```

#### places 테이블

| 인덱스명 | 유형 | 대상 컬럼 | 조건 | 근거 API |
|---------|------|----------|------|---------|
| idx_places_user_id_visited_at | B-Tree | (user_id, visited_at DESC) | WHERE deleted_at IS NULL | P-01(장소 목록 조회 - 기본 정렬: 방문일 최신순) |
| idx_places_user_id_created_at | B-Tree | (user_id, created_at DESC) | WHERE deleted_at IS NULL | P-01(장소 목록 조회 - 등록일순 정렬) |
| idx_places_user_id_rating | B-Tree | (user_id, rating) | WHERE deleted_at IS NULL | P-01(장소 목록 조회 - 평점 필터링) |
| idx_places_visited_at_range | B-Tree | (user_id, visited_at) | WHERE deleted_at IS NULL | P-01(방문일 범위 필터링: visitedFrom ~ visitedTo) |
| idx_places_user_map | B-Tree | (user_id, id) | WHERE deleted_at IS NULL | P-01(view=map 전체 조회) |

```
-- P-01 장소 목록 기본 쿼리 (기본 정렬):
-- SELECT * FROM places
-- WHERE user_id = $1 AND deleted_at IS NULL
-- ORDER BY visited_at DESC, id DESC
-- LIMIT 20 OFFSET $2
--
-- EXPLAIN ANALYZE 기대 결과:
-- Index Scan using idx_places_user_id_visited_at on places
-- (선택도: user_id 기준 평균 수백~수천 건 예상)
--
-- 부분 인덱스(deleted_at IS NULL)로 삭제된 장소는 인덱스에서 제외,
-- 실제 서비스 데이터의 99% 이상이 NULL임을 고려한 최적화
```

#### place_category 테이블

| 인덱스명 | 유형 | 대상 컬럼 | 조건 | 근거 API |
|---------|------|----------|------|---------|
| idx_place_category_category_id | B-Tree | category_id | - | C-04(카테고리 삭제 전 장소 존재 확인), P-01(카테고리 필터링) |

```
-- C-04 삭제 전 검증 쿼리:
-- SELECT 1 FROM place_category WHERE category_id = $1 LIMIT 1
-- 카테고리 삭제 시 사용 중 여부 빠른 확인을 위한 인덱스
--
-- P-01 카테고리 필터링 쿼리:
-- SELECT place_id FROM place_category WHERE category_id = ANY($1)
```

#### place_photos 테이블

| 인덱스명 | 유형 | 대상 컬럼 | 조건 | 근거 API |
|---------|------|----------|------|---------|
| idx_place_photos_place_id | B-Tree | (place_id, sort_order) | - | P-03(장소 상세 조회 시 사진 목록), PH-01(사진 업로드 시 개수 확인) |

```
-- P-03 장소 상세 조회 사진 쿼리:
-- SELECT * FROM place_photos WHERE place_id = $1 ORDER BY sort_order
-- PH-01 사진 개수 확인:
-- SELECT COUNT(*) FROM place_photos WHERE place_id = $1
-- sort_order 포함 복합 인덱스로 ORDER BY 정렬 비용 제거 (Index Scan 후 filesort 없음)
```

#### place_tags 테이블

| 인덱스명 | 유형 | 대상 컬럼 | 조건 | 근거 API |
|---------|------|----------|------|---------|
| idx_place_tags_place_id | B-Tree | place_id | - | P-03(장소 상세 조회 시 태그 목록) |
| idx_place_tags_tag | B-Tree | tag | - | P-01(태그 필터링: tags 파라미터) |

```
-- P-01 태그 필터링 쿼리:
-- SELECT DISTINCT place_id FROM place_tags
-- WHERE tag = ANY($1) AND place_id IN (/* 사용자 장소 서브쿼리 */)
```

#### refresh_tokens 테이블

| 인덱스명 | 유형 | 대상 컬럼 | 조건 | 근거 API |
|---------|------|----------|------|---------|
| idx_refresh_tokens_token_hash | B-Tree (UNIQUE) | token_hash | - | A-04(토큰 갱신: 토큰 해시로 조회) |
| idx_refresh_tokens_user_id_active | B-Tree | user_id | WHERE revoked_at IS NULL AND expires_at > NOW() | A-03(로그아웃: 사용자의 유효 토큰 무효화) |

```
-- A-04 토큰 갱신 쿼리:
-- SELECT * FROM refresh_tokens
-- WHERE token_hash = $1 AND revoked_at IS NULL AND expires_at > NOW()
-- token_hash UNIQUE 인덱스로 O(1) 조회
--
-- A-03 로그아웃 쿼리:
-- UPDATE refresh_tokens SET revoked_at = NOW()
-- WHERE user_id = $1 AND revoked_at IS NULL
-- 부분 인덱스로 유효한 토큰만 인덱스에 포함
```

### 3.3 Full-Text 검색 고려사항

> FR-SEARCH-02: 키워드 검색 (장소명, 주소, 메모, 태그)

현재 데이터 규모(사용자당 수백~수천 건 예상)에서는 `ILIKE '%keyword%'` 검색으로 충분하다.
향후 데이터 증가 시 아래 방향으로 전환을 검토한다:

1. **단기 (현재 적용)**: `places.name`, `places.address`, `places.memo`에 `ILIKE` + `place_tags.tag`에 B-Tree 인덱스
2. **중기 (10만 건 이상)**: `to_tsvector('korean', name || ' ' || address || ' ' || memo)` 생성 컬럼 + GIN 인덱스
3. **장기 (100만 건 이상)**: Elasticsearch 연동 또는 pg_trgm GIN 인덱스 도입

---

## 4. 파티셔닝 전략

### 4.1 현재 판단

초기 서비스 규모(예상 동시 사용자 100명, 사용자당 장소 수백 건)에서는 **파티셔닝을 적용하지 않는다.**

파티셔닝은 단일 테이블 수백만 건 이상에서 효과가 있으며, 관리 복잡도와 운영 비용이 증가하므로 현 단계에서는 부적절하다.

### 4.2 향후 파티셔닝 전환 기준

`places` 테이블 총 레코드 **500만 건 초과** 시 아래 전략을 검토한다.

```sql
-- 범위 파티셔닝 (visited_at 기준 연도별 분리) 예시
CREATE TABLE places (
    ...
) PARTITION BY RANGE (visited_at);

CREATE TABLE places_2024 PARTITION OF places
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE places_2025 PARTITION OF places
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

**근거**: 통계 API(S-02 월별 통계, S-04 지역별 통계)는 `visited_at` 기준 범위 조회가 잦으므로, Range Partitioning이 적합하다.

---

## 5. VACUUM / Autovacuum 설정 권고사항

### 5.1 기본 원칙

PostgreSQL 16의 기본 Autovacuum 설정은 대부분의 OLTP 워크로드에 적합하나, 다음 테이블은 갱신/삭제 빈도가 높으므로 별도 조정이 필요하다.

### 5.2 테이블별 Autovacuum 설정

#### refresh_tokens (갱신/삭제 빈번)

로그인·로그아웃·토큰 갱신마다 INSERT/UPDATE/논리 삭제가 발생하여 Dead Tuple이 빠르게 누적된다.

```sql
ALTER TABLE refresh_tokens SET (
    autovacuum_vacuum_scale_factor = 0.01,   -- 기본 0.2 → 1% 변경 시 VACUUM 실행
    autovacuum_analyze_scale_factor = 0.005, -- 기본 0.1 → 0.5% 변경 시 ANALYZE 실행
    autovacuum_vacuum_cost_delay = 2         -- VACUUM 실행 지연 최소화 (ms)
);
```

#### places (소프트 딜리트로 Dead Tuple 누적 가능)

삭제 빈도가 낮으나, 소프트 딜리트 패턴상 `deleted_at` UPDATE가 발생하므로 기본값보다 소폭 낮게 설정한다.

```sql
ALTER TABLE places SET (
    autovacuum_vacuum_scale_factor = 0.05,   -- 기본 0.2 → 5%로 조정
    autovacuum_analyze_scale_factor = 0.02
);
```

### 5.3 만료 토큰 정리 정책

`refresh_tokens` 테이블의 만료·무효화된 레코드를 주기적으로 물리 삭제한다.

```sql
-- 매일 새벽 2시 배치 실행 권고 (Spring Batch 또는 pg_cron)
DELETE FROM refresh_tokens
WHERE expires_at < NOW() - INTERVAL '1 day'
   OR revoked_at IS NOT NULL;
```

**주의**: 삭제 후 `ANALYZE refresh_tokens;` 수동 실행을 권고하여 플래너 통계를 최신화한다.

### 5.4 VACUUM 상태 모니터링

```sql
-- Dead Tuple 누적 현황 확인
SELECT relname,
       n_dead_tup,
       n_live_tup,
       round(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2) AS dead_ratio_pct,
       last_autovacuum,
       last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_dead_tup DESC;
```

---

## 6. 설계 결정 사항 및 근거

| 항목 | 결정 | 근거 |
|------|------|------|
| users.id 타입 | UUID | 순차 ID 노출 시 타 사용자 ID 추측 가능 → 보안 강화 |
| places.id 타입 | BIGSERIAL | API 응답에서 placeId로 노출되나, URL 예측이 큰 보안 위협 아님. UUID 대비 인덱스 효율 우수 |
| 태그 저장 방식 | 별도 테이블(place_tags) | `tags` 컬럼을 TEXT[]로 저장하면 부분 인덱스/JOIN 효율 저하. 정규화로 검색 성능 확보 |
| 카테고리 N:M | place_category 연결 테이블 | 장소 1개 → 다중 카테고리 선택 요구사항 반영 |
| Soft Delete 범위 | places, users | place_photos, place_tags, place_category는 ON DELETE CASCADE로 물리 삭제. 실질적 복구 대상은 장소와 사용자 계정만 해당 |
| refresh_token 저장 | token_hash (SHA-256) | 원본 토큰 DB 저장 시 탈취 위험 → 해시 저장으로 원본 복원 불가 |
| 파티셔닝 | 미적용 (초기) | 현 규모에서 관리 복잡도 대비 효과 없음. 임계점 도달 시 전환 |
