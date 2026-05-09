# Shelfy - 데이터 모델 초안 (Data Model Draft)

- 작성일: 2026-05-09
- 작성자: Planner
- 버전: v1.0.0
- 대상 DB: PostgreSQL

---

## 목차

1. [엔티티 관계도 (ERD 텍스트)](#1-엔티티-관계도-erd-텍스트)
2. [엔티티 상세 정의](#2-엔티티-상세-정의)
3. [Enum 정의](#3-enum-정의)
4. [인덱스 요구사항 (DBA 협의 필요)](#4-인덱스-요구사항-dba-협의-필요)
5. [데이터 보존 정책](#5-데이터-보존-정책)

---

## 1. 엔티티 관계도 (ERD 텍스트)

```
[users]
  |
  |--< [items]                  (1:N, 셀러-상품)
  |       |
  |       |--< [item_images]    (1:N, 상품-이미지)
  |       |
  |       |--< [subscription_plans]  (1:N, 상품-구독플랜)
  |       |          |
  |       |          |--< [subscriptions]  (1:N, 플랜-구독)
  |       |                   |
  |       |                   +--- [users] (N:1, 구독자)
  |       |
  |       |--< [orders]        (1:N, 상품-주문)
  |               |
  |               +--- [users] (N:1, 구매자)
  |
  |--< [subscriptions]          (1:N, 유저-구독내역)
  |
  |--< [orders]                 (1:N, 유저-구매내역)
  |
  |--- [email_verifications]    (1:1, 유저-인증정보)
  |
  |--- [password_reset_tokens]  (1:N, 유저-재설정토큰)
  |
  |--- [refresh_tokens]         (1:N, 유저-리프레시토큰)

[files]
  (items.thumbnail_image_id → files.id)
  (item_images.file_id → files.id)
  (users.profile_image_id → files.id)
```

---

## 2. 엔티티 상세 정의

### 2.1 users (사용자)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | 사용자 ID |
| email | VARCHAR(255) | Y | UNIQUE | - | 이메일 (로그인 ID) |
| password_hash | VARCHAR(255) | Y | - | - | bcrypt 해시 비밀번호 |
| nickname | VARCHAR(20) | Y | UNIQUE | - | 닉네임 (공개) |
| bio | VARCHAR(200) | N | - | NULL | 자기 소개 |
| profile_image_id | BIGINT | N | FK(files.id) | NULL | 프로필 이미지 |
| email_verified | BOOLEAN | Y | - | false | 이메일 인증 여부 |
| agree_terms | BOOLEAN | Y | - | - | 이용약관 동의 |
| agree_privacy | BOOLEAN | Y | - | - | 개인정보처리방침 동의 |
| agree_marketing | BOOLEAN | Y | - | false | 마케팅 수신 동의 |
| login_failed_count | SMALLINT | Y | - | 0 | 연속 로그인 실패 횟수 |
| locked_until | TIMESTAMPTZ | N | - | NULL | 계정 잠금 해제 시각 |
| deleted_at | TIMESTAMPTZ | N | - | NULL | 소프트 삭제 시각 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 가입 일시 |
| updated_at | TIMESTAMPTZ | Y | - | NOW() | 최종 수정 일시 |

---

### 2.2 email_verifications (이메일 인증)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | ID |
| user_id | BIGINT | Y | FK(users.id) | - | 사용자 ID |
| token | VARCHAR(255) | Y | UNIQUE | - | 인증 토큰 (UUID) |
| expires_at | TIMESTAMPTZ | Y | - | - | 만료 시각 (발급 후 24시간) |
| verified_at | TIMESTAMPTZ | N | - | NULL | 인증 완료 시각 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 생성 일시 |

---

### 2.3 password_reset_tokens (비밀번호 재설정 토큰)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | ID |
| user_id | BIGINT | Y | FK(users.id) | - | 사용자 ID |
| token | VARCHAR(255) | Y | UNIQUE | - | 재설정 토큰 (UUID) |
| expires_at | TIMESTAMPTZ | Y | - | - | 만료 시각 (발급 후 1시간) |
| used_at | TIMESTAMPTZ | N | - | NULL | 사용 완료 시각 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 생성 일시 |

---

### 2.4 refresh_tokens (리프레시 토큰)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | ID |
| user_id | BIGINT | Y | FK(users.id) | - | 사용자 ID |
| token_hash | VARCHAR(255) | Y | UNIQUE | - | 토큰 해시값 |
| expires_at | TIMESTAMPTZ | Y | - | - | 만료 시각 (14일) |
| revoked_at | TIMESTAMPTZ | N | - | NULL | 무효화 시각 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 생성 일시 |

---

### 2.5 files (업로드 파일)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | 파일 ID |
| uploader_id | BIGINT | Y | FK(users.id) | - | 업로드 사용자 |
| file_type | VARCHAR(20) | Y | - | - | `ITEM_IMAGE` / `PROFILE_IMAGE` |
| original_name | VARCHAR(255) | Y | - | - | 원본 파일명 |
| stored_name | VARCHAR(255) | Y | UNIQUE | - | 저장 파일명 (UUID 기반) |
| cdn_url | VARCHAR(500) | Y | - | - | CDN 접근 URL |
| file_size | BIGINT | Y | - | - | 파일 크기 (bytes) |
| mime_type | VARCHAR(50) | Y | - | - | `image/jpeg` 등 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 업로드 일시 |

---

### 2.6 items (상품)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | 상품 ID |
| seller_id | BIGINT | Y | FK(users.id) | - | 셀러 사용자 ID |
| title | VARCHAR(100) | Y | - | - | 상품명 |
| description | TEXT | Y | - | - | 상품 설명 |
| category | VARCHAR(30) | Y | - | - | 카테고리 코드 |
| sale_type | VARCHAR(10) | Y | - | - | `PURCHASE` / `SUBSCRIBE` / `BOTH` |
| price | INTEGER | N | - | NULL | 단일 구매 가격 (원) |
| thumbnail_image_id | BIGINT | N | FK(files.id) | NULL | 대표 이미지 |
| tags | VARCHAR(20)[] | N | - | '{}' | 태그 배열 (PostgreSQL Array) |
| status | VARCHAR(10) | Y | - | 'DRAFT' | `DRAFT` / `PUBLISHED` |
| view_count | BIGINT | Y | - | 0 | 조회수 |
| deleted_at | TIMESTAMPTZ | N | - | NULL | 소프트 삭제 시각 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 등록 일시 |
| updated_at | TIMESTAMPTZ | Y | - | NOW() | 최종 수정 일시 |

---

### 2.7 item_images (상품 이미지)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | ID |
| item_id | BIGINT | Y | FK(items.id) | - | 상품 ID |
| file_id | BIGINT | Y | FK(files.id) | - | 파일 ID |
| sort_order | SMALLINT | Y | - | 0 | 이미지 순서 |
| is_thumbnail | BOOLEAN | Y | - | false | 대표 이미지 여부 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 생성 일시 |

---

### 2.8 subscription_plans (구독 플랜)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | 플랜 ID |
| item_id | BIGINT | Y | FK(items.id) | - | 상품 ID |
| plan_name | VARCHAR(50) | Y | - | - | 플랜명 (예: Basic) |
| period | VARCHAR(10) | Y | - | - | `MONTHLY` / `QUARTERLY` / `YEARLY` |
| plan_price | INTEGER | Y | - | - | 구독 가격 (원) |
| description | VARCHAR(500) | N | - | NULL | 플랜 설명 |
| is_active | BOOLEAN | Y | - | true | 플랜 활성 여부 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 생성 일시 |
| updated_at | TIMESTAMPTZ | Y | - | NOW() | 최종 수정 일시 |

---

### 2.9 orders (구매 주문)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | 주문 ID |
| buyer_id | BIGINT | Y | FK(users.id) | - | 구매자 사용자 ID |
| item_id | BIGINT | Y | FK(items.id) | - | 상품 ID |
| item_title | VARCHAR(100) | Y | - | - | 주문 시점 상품명 (스냅샷) |
| amount | INTEGER | Y | - | - | 결제 금액 (원) |
| payment_method | VARCHAR(20) | Y | - | - | `CARD` / `KAKAO_PAY` / `NAVER_PAY` |
| pg_transaction_id | VARCHAR(255) | N | UNIQUE | NULL | PG사 거래 ID |
| status | VARCHAR(20) | Y | - | - | `PENDING` / `COMPLETED` / `REFUNDED` / `FAILED` |
| refund_reason | VARCHAR(500) | N | - | NULL | 환불 사유 |
| refunded_at | TIMESTAMPTZ | N | - | NULL | 환불 처리 시각 |
| paid_at | TIMESTAMPTZ | N | - | NULL | 결제 완료 시각 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 주문 생성 일시 |
| updated_at | TIMESTAMPTZ | Y | - | NOW() | 최종 수정 일시 |

---

### 2.10 subscriptions (구독)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | 구독 ID |
| subscriber_id | BIGINT | Y | FK(users.id) | - | 구독자 사용자 ID |
| item_id | BIGINT | Y | FK(items.id) | - | 상품 ID |
| plan_id | BIGINT | Y | FK(subscription_plans.id) | - | 구독 플랜 ID |
| plan_name | VARCHAR(50) | Y | - | - | 구독 시점 플랜명 (스냅샷) |
| amount | INTEGER | Y | - | - | 결제 금액 (원) |
| payment_method | VARCHAR(20) | Y | - | - | 결제 수단 |
| status | VARCHAR(20) | Y | - | - | `ACTIVE` / `CANCEL_REQUESTED` / `CANCELLED` / `SUSPENDED` |
| started_at | TIMESTAMPTZ | Y | - | NOW() | 구독 시작 일시 |
| next_billing_at | TIMESTAMPTZ | Y | - | - | 다음 결제 예정 일시 |
| cancelled_at | TIMESTAMPTZ | N | - | NULL | 해지 신청 일시 |
| active_until | TIMESTAMPTZ | N | - | NULL | 서비스 이용 가능 만료 일시 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 생성 일시 |
| updated_at | TIMESTAMPTZ | Y | - | NOW() | 최종 수정 일시 |

---

### 2.11 subscription_payments (구독 결제 이력)

| 컬럼명 | 데이터 타입 | NOT NULL | PK/FK | 기본값 | 설명 |
|---|---|:---:|---|---|---|
| id | BIGSERIAL | Y | PK | - | 결제 이력 ID |
| subscription_id | BIGINT | Y | FK(subscriptions.id) | - | 구독 ID |
| amount | INTEGER | Y | - | - | 결제 금액 (원) |
| pg_transaction_id | VARCHAR(255) | N | UNIQUE | NULL | PG사 거래 ID |
| status | VARCHAR(20) | Y | - | - | `SUCCESS` / `FAILED` |
| billing_at | TIMESTAMPTZ | Y | - | - | 결제 예정 일시 |
| paid_at | TIMESTAMPTZ | N | - | NULL | 실제 결제 완료 일시 |
| failed_reason | VARCHAR(255) | N | - | NULL | 실패 사유 |
| created_at | TIMESTAMPTZ | Y | - | NOW() | 생성 일시 |

---

## 3. Enum 정의

### 3.1 sale_type (판매 유형)

| 값 | 설명 |
|---|---|
| PURCHASE | 단일 구매만 가능 |
| SUBSCRIBE | 구독만 가능 |
| BOTH | 단일 구매 + 구독 모두 가능 |

### 3.2 item_status (상품 상태)

| 값 | 설명 |
|---|---|
| DRAFT | 비공개 (임시저장) |
| PUBLISHED | 공개 중 |

### 3.3 subscription_period (구독 주기)

| 값 | 설명 |
|---|---|
| MONTHLY | 월간 (1개월) |
| QUARTERLY | 분기 (3개월) |
| YEARLY | 연간 (1년) |

### 3.4 subscription_status (구독 상태)

| 값 | 설명 |
|---|---|
| ACTIVE | 활성 구독 중 |
| CANCEL_REQUESTED | 해지 신청됨 (기간 만료 전) |
| CANCELLED | 해지 완료 |
| SUSPENDED | 결제 실패로 일시 정지 |

### 3.5 order_status (주문 상태)

| 값 | 설명 |
|---|---|
| PENDING | 결제 진행 중 |
| COMPLETED | 결제 완료 |
| REFUNDED | 환불 완료 |
| FAILED | 결제 실패 |

### 3.6 category (카테고리)

| 값 | 표시명 |
|---|---|
| DIGITAL_CONTENT | 디지털 콘텐츠 |
| COURSE | 강의/교육 |
| TEMPLATE | 템플릿/자료 |
| PHOTO | 사진/그래픽 |
| MUSIC | 음악/사운드 |
| SOFTWARE | 소프트웨어/앱 |
| OTHER | 기타 |

### 3.7 file_type (파일 유형)

| 값 | 설명 |
|---|---|
| ITEM_IMAGE | 상품 이미지 |
| PROFILE_IMAGE | 프로필 이미지 |

---

## 4. 인덱스 요구사항 (DBA 협의 필요)

> 아래 인덱스 목록은 API 조회 패턴 기반 Planner 초안이다. 실제 인덱스 생성 여부 및 구체적 방식은 DBA와 협의하여 확정한다.

### 4.1 users

| 인덱스 대상 | 유형 | 사유 |
|---|---|---|
| email | UNIQUE | 로그인, 중복 체크 |
| nickname | UNIQUE | 프로필 조회, 중복 체크 |
| deleted_at | - | 소프트 삭제 필터링 |

### 4.2 items

| 인덱스 대상 | 유형 | 사유 |
|---|---|---|
| seller_id | - | 셀러별 상품 조회 |
| status, deleted_at | 복합 | 공개 상품 목록 조회 |
| category, status | 복합 | 카테고리 필터 조회 |
| created_at | - | 최신순 정렬 |
| title, description, tags | 전문 검색 (tsvector) | 키워드 검색 (DBA 확인 필요) |

### 4.3 orders

| 인덱스 대상 | 유형 | 사유 |
|---|---|---|
| buyer_id | - | 구매자별 주문 조회 |
| item_id | - | 상품별 주문 조회 |
| status | - | 상태별 필터 |
| paid_at | - | 날짜 범위 조회 |

### 4.4 subscriptions

| 인덱스 대상 | 유형 | 사유 |
|---|---|---|
| subscriber_id | - | 구독자별 조회 |
| item_id | - | 상품별 구독자 수 집계 |
| status | - | 활성 구독 필터 |
| next_billing_at | - | 정기 결제 배치 처리 |

### 4.5 subscription_payments

| 인덱스 대상 | 유형 | 사유 |
|---|---|---|
| subscription_id | - | 구독별 결제 이력 조회 |
| status, billing_at | 복합 | 배치 결제 처리 대상 조회 |

---

## 5. 데이터 보존 정책

| 테이블 | 정책 |
|---|---|
| users | 소프트 삭제 (deleted_at 기록). 30일 후 익명화 처리 고려 |
| items | 소프트 삭제 (deleted_at 기록). 주문/구독 이력 참조 보존 |
| orders | 물리 삭제 없음. 법적 보존 의무 (전자상거래법: 5년) |
| subscription_payments | 물리 삭제 없음. 법적 보존 의무 (5년) |
| email_verifications | 인증 완료 또는 만료 후 30일 이후 삭제 (배치) |
| password_reset_tokens | 사용 완료 또는 만료 후 즉시 삭제 처리 |
| refresh_tokens | 만료 또는 revoke 후 7일 이후 삭제 (배치) |
| files | 연결된 엔티티 삭제 후 CDN 파일 별도 정리 필요 (DBA/Infra 협의) |

---

## 6. 주요 설계 결정 사항 (Design Decisions)

| 항목 | 결정 | 근거 |
|---|---|---|
| 상품명/금액 스냅샷 저장 | orders / subscriptions에 item_title, amount 비정규화 | 상품 수정 후에도 기존 주문 내역 보존 필요 |
| 태그 저장 방식 | PostgreSQL Array 타입 (`VARCHAR(20)[]`) | 별도 tags 테이블 불필요, 단순 조회 충분 |
| 검색 구현 | PostgreSQL tsvector 전문 검색 (초기), 확장 시 Elasticsearch 연동 고려 | 초기 트래픽에는 DB 내 전문 검색으로 충분 |
| Refresh Token 저장 | DB 저장 (token_hash) + HttpOnly 쿠키 | 강제 로그아웃, 다중 기기 토큰 무효화 지원 |
| 구독 상태 전이 | ACTIVE -> CANCEL_REQUESTED -> CANCELLED | 현재 구독 기간 유지 후 자동 해지 정책 반영 |
| 플랫폼 수수료 | 서비스 레이어에서 계산, DB에는 실결제 금액만 저장 | 수수료 정책 변경 시 코드 수정으로 대응 |
