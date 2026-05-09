# Shelfy - API 요구사항 정의서 (API Requirements)

- 작성일: 2026-05-09
- 작성자: Planner
- 버전: v1.0.0

---

## 목차

1. [공통 규약](#1-공통-규약)
2. [인증 API](#2-인증-api)
3. [상품 API](#3-상품-api)
4. [탐색 및 검색 API](#4-탐색-및-검색-api)
5. [구매(주문) API](#5-구매주문-api)
6. [구독 API](#6-구독-api)
7. [사용자 프로필 API](#7-사용자-프로필-api)
8. [파일 업로드 API](#8-파일-업로드-api)

---

## 1. 공통 규약

### 1.1 Base URL

```
개발: https://api-dev.shelfy.io/api/v1
운영: https://api.shelfy.io/api/v1
```

### 1.2 인증 방식

- 인증이 필요한 API는 요청 헤더에 JWT Bearer 토큰 포함
- `Authorization: Bearer {accessToken}`
- Access Token 만료 시 `/auth/token/refresh` 엔드포인트로 갱신

### 1.3 공통 요청 헤더

| 헤더명 | 필수 | 설명 |
|---|---|---|
| Content-Type | Y | `application/json` (파일 업로드 시 `multipart/form-data`) |
| Authorization | 조건부 | 인증 필요 API에만 필수 |
| Accept-Language | N | `ko` / `en` (기본값: `ko`) |

### 1.4 공통 응답 형식

**성공 응답**

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**목록 응답 (페이지네이션)**

```json
{
  "success": true,
  "data": {
    "content": [ ... ],
    "page": 0,
    "size": 20,
    "totalElements": 150,
    "totalPages": 8,
    "first": true,
    "last": false
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**오류 응답**

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "AUTH-E001",
    "message": "이미 사용 중인 이메일입니다."
  },
  "timestamp": "2026-05-09T12:00:00Z"
}
```

### 1.5 HTTP 상태 코드

| 상태 코드 | 의미 |
|---|---|
| 200 | 성공 (조회, 수정) |
| 201 | 생성 성공 |
| 204 | 성공 (응답 바디 없음, 삭제) |
| 400 | 잘못된 요청 (유효성 검사 실패) |
| 401 | 인증 실패 또는 토큰 만료 |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 409 | 충돌 (중복 데이터) |
| 422 | 처리 불가 엔티티 (비즈니스 로직 오류) |
| 500 | 서버 내부 오류 |

---

## 2. 인증 API

### 2.1 회원가입

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/auth/signup` |
| 인증 필요 | 없음 |

**요청 바디**

```json
{
  "email": "user@example.com",
  "password": "Password1!",
  "passwordConfirm": "Password1!",
  "nickname": "shelfy_user",
  "agreeTerms": true,
  "agreePrivacy": true,
  "agreeMarketing": false
}
```

**응답 바디 (201)**

```json
{
  "success": true,
  "data": {
    "userId": 1001,
    "email": "user@example.com",
    "nickname": "shelfy_user"
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 409 | AUTH-E001 | 이메일 중복 |
| 409 | AUTH-E002 | 닉네임 중복 |
| 400 | AUTH-E003 | 비밀번호 불일치 |
| 400 | AUTH-E004 | 이메일 형식 오류 |
| 400 | AUTH-E005 | 비밀번호 규칙 위반 |
| 400 | AUTH-E006 | 필수 동의 누락 |

---

### 2.2 이메일 인증

| 항목 | 내용 |
|---|---|
| Method | `GET` |
| URL | `/auth/verify-email?token={verifyToken}` |
| 인증 필요 | 없음 |

**쿼리 파라미터**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| token | String | Y | 이메일로 발송된 인증 토큰 |

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "message": "이메일 인증이 완료되었습니다."
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 400 | AUTH-E010 | 인증 토큰 만료 |
| 400 | AUTH-E011 | 유효하지 않은 토큰 |
| 409 | AUTH-E012 | 이미 인증 완료 |

---

### 2.3 이메일 인증 재발송

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/auth/resend-verification` |
| 인증 필요 | 없음 |

**요청 바디**

```json
{
  "email": "user@example.com"
}
```

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "message": "인증 이메일을 재발송했습니다."
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

---

### 2.4 로그인

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/auth/login` |
| 인증 필요 | 없음 |

**요청 바디**

```json
{
  "email": "user@example.com",
  "password": "Password1!"
}
```

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "tokenType": "Bearer",
    "expiresIn": 3600
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**응답 Set-Cookie (HttpOnly)**

```
Set-Cookie: refreshToken={token}; HttpOnly; Secure; SameSite=Strict; Max-Age=1209600; Path=/auth/token
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 401 | AUTH-E020 | 이메일 미존재 또는 비밀번호 불일치 |
| 403 | AUTH-E021 | 계정 잠금 상태 |
| 403 | AUTH-E022 | 탈퇴된 계정 |

---

### 2.5 로그아웃

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/auth/logout` |
| 인증 필요 | Bearer Token |

**요청 바디**: 없음

**응답 (204)**: 응답 바디 없음, refreshToken 쿠키 만료 처리

---

### 2.6 Access Token 갱신

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/auth/token/refresh` |
| 인증 필요 | refreshToken 쿠키 |

**요청**: Cookie에 refreshToken 자동 포함 (HttpOnly)

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "tokenType": "Bearer",
    "expiresIn": 3600
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 401 | AUTH-E030 | Refresh Token 만료 |
| 401 | AUTH-E031 | 유효하지 않은 Refresh Token |

---

### 2.7 비밀번호 재설정 요청

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/auth/forgot-password` |
| 인증 필요 | 없음 |

**요청 바디**

```json
{
  "email": "user@example.com"
}
```

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "message": "비밀번호 재설정 이메일을 발송했습니다."
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

> 보안상 이메일 존재 여부와 관계없이 동일 응답 반환

---

### 2.8 비밀번호 재설정

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/auth/reset-password` |
| 인증 필요 | 없음 |

**요청 바디**

```json
{
  "token": "reset-token-string",
  "newPassword": "NewPassword1!",
  "newPasswordConfirm": "NewPassword1!"
}
```

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "message": "비밀번호가 재설정되었습니다."
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

---

### 2.9 회원 탈퇴

| 항목 | 내용 |
|---|---|
| Method | `DELETE` |
| URL | `/auth/me` |
| 인증 필요 | Bearer Token |

**요청 바디**

```json
{
  "password": "Password1!"
}
```

**응답 (204)**: 응답 바디 없음

---

## 3. 상품 API

### 3.1 상품 등록

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/items` |
| 인증 필요 | Bearer Token (이메일 인증 완료 필수) |
| Content-Type | `application/json` |

**요청 바디**

```json
{
  "title": "포토샵 작업 템플릿 50종",
  "description": "전문 디자이너가 제작한 포토샵 PSD 템플릿...",
  "category": "TEMPLATE",
  "saleType": "BOTH",
  "price": 15000,
  "subscriptionPlans": [
    {
      "planName": "Basic",
      "period": "MONTHLY",
      "planPrice": 5000,
      "description": "월간 기본 접근권"
    },
    {
      "planName": "Premium",
      "period": "YEARLY",
      "planPrice": 50000,
      "description": "연간 프리미엄 (2개월 무료)"
    }
  ],
  "imageIds": ["img-uuid-001", "img-uuid-002"],
  "thumbnailIndex": 0,
  "tags": ["포토샵", "PSD", "템플릿", "디자인"],
  "status": "PUBLISHED"
}
```

> 이미지는 `/files/upload` API로 먼저 업로드 후 반환된 imageId를 사용

**응답 바디 (201)**

```json
{
  "success": true,
  "data": {
    "itemId": 5001
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 403 | ITEM-E001 | 이메일 미인증 |
| 400 | ITEM-E005 | 가격 범위 오류 |
| 400 | ITEM-E006 | 유효하지 않은 카테고리 |
| 400 | ITEM-E007 | 구독 플랜 누락 (구독 타입인 경우) |

---

### 3.2 상품 수정

| 항목 | 내용 |
|---|---|
| Method | `PUT` |
| URL | `/items/{itemId}` |
| 인증 필요 | Bearer Token (본인만) |

**요청 바디**: 3.1 등록 요청과 동일 구조 (변경할 필드만 포함 가능 - PATCH 방식과 동일하게 처리)

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "itemId": 5001,
    "updatedAt": "2026-05-09T13:00:00Z"
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 403 | ITEM-E020 | 권한 없음 (본인 아님) |
| 404 | ITEM-E022 | 상품 없음 |
| 422 | ITEM-E021 | 구독자 존재하는 플랜 가격 변경 시도 |

---

### 3.3 상품 삭제

| 항목 | 내용 |
|---|---|
| Method | `DELETE` |
| URL | `/items/{itemId}` |
| 인증 필요 | Bearer Token (본인만) |

**응답 (204)**: 응답 바디 없음

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 403 | ITEM-E031 | 권한 없음 |
| 422 | ITEM-E030 | 활성 구독자 존재 |

---

### 3.4 상품 상태 변경 (공개/비공개)

| 항목 | 내용 |
|---|---|
| Method | `PATCH` |
| URL | `/items/{itemId}/status` |
| 인증 필요 | Bearer Token (본인만) |

**요청 바디**

```json
{
  "status": "PUBLISHED"
}
```

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "itemId": 5001,
    "status": "PUBLISHED"
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

---

### 3.5 내 상품 목록 조회 (셀러)

| 항목 | 내용 |
|---|---|
| Method | `GET` |
| URL | `/items/my` |
| 인증 필요 | Bearer Token |

**쿼리 파라미터**

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| status | String | ALL | `ALL` / `DRAFT` / `PUBLISHED` / `DELETED` |
| page | Integer | 0 | 페이지 번호 |
| size | Integer | 20 | 페이지당 항목 수 (최대 100) |
| sort | String | createdAt | `createdAt` / `title` / `price` |
| order | String | DESC | `ASC` / `DESC` |

**응답 바디 (200)**: 페이지네이션 포맷, 항목 내 itemId / title / status / price / createdAt / thumbnailUrl

---

### 3.6 상품 상세 조회

| 항목 | 내용 |
|---|---|
| Method | `GET` |
| URL | `/items/{itemId}` |
| 인증 필요 | 없음 (DRAFT 상태는 본인만 조회 가능) |

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "itemId": 5001,
    "title": "포토샵 작업 템플릿 50종",
    "description": "전문 디자이너가 제작한...",
    "category": "TEMPLATE",
    "saleType": "BOTH",
    "price": 15000,
    "subscriptionPlans": [
      {
        "planId": 101,
        "planName": "Basic",
        "period": "MONTHLY",
        "planPrice": 5000,
        "description": "월간 기본 접근권"
      }
    ],
    "images": [
      {
        "imageId": "img-uuid-001",
        "url": "https://cdn.shelfy.io/images/img-uuid-001.jpg",
        "isThumbnail": true
      }
    ],
    "tags": ["포토샵", "PSD"],
    "status": "PUBLISHED",
    "viewCount": 1240,
    "seller": {
      "userId": 1001,
      "nickname": "shelfy_user",
      "profileImageUrl": "https://cdn.shelfy.io/profiles/1001.jpg",
      "itemCount": 12
    },
    "createdAt": "2026-04-01T09:00:00Z",
    "updatedAt": "2026-05-01T11:00:00Z"
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 404 | BROWSE-E001 | 상품 없음 |
| 403 | BROWSE-E002 | 비공개 상품 (본인 제외) |

---

## 4. 탐색 및 검색 API

### 4.1 상품 목록 탐색 (피드)

| 항목 | 내용 |
|---|---|
| Method | `GET` |
| URL | `/items` |
| 인증 필요 | 없음 |

**쿼리 파라미터**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| category | String | N | 카테고리 필터 |
| saleType | String | N | `PURCHASE` / `SUBSCRIBE` / `BOTH` |
| minPrice | Integer | N | 최소 가격 |
| maxPrice | Integer | N | 최대 가격 |
| sort | String | N | `latest` / `popular` / `lowPrice` / `highPrice` |
| page | Integer | N | 기본값: 0 |
| size | Integer | N | 기본값: 20, 최대 50 |

**응답 바디 (200)**: 페이지네이션 포맷, 항목 내 itemId / title / price / saleType / thumbnailUrl / seller(nickname)

---

### 4.2 상품 검색

| 항목 | 내용 |
|---|---|
| Method | `GET` |
| URL | `/items/search` |
| 인증 필요 | 없음 |

**쿼리 파라미터**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| q | String | Y | 검색 키워드 (1~100자) |
| category | String | N | 카테고리 필터 |
| saleType | String | N | 판매 유형 필터 |
| page | Integer | N | 기본값: 0 |
| size | Integer | N | 기본값: 20 |

**응답 바디 (200)**: 4.1과 동일 구조 + `totalElements`(검색 총 결과 수) 포함

---

## 5. 구매(주문) API

### 5.1 단일 구매 주문 생성

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/orders` |
| 인증 필요 | Bearer Token |

**요청 바디**

```json
{
  "itemId": 5001,
  "paymentMethod": "CARD"
}
```

**응답 바디 (201)**

```json
{
  "success": true,
  "data": {
    "orderId": 20001,
    "itemId": 5001,
    "itemTitle": "포토샵 작업 템플릿 50종",
    "amount": 15000,
    "paymentMethod": "CARD",
    "status": "COMPLETED",
    "paidAt": "2026-05-09T12:00:00Z"
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 422 | ORDER-E001 | 본인 상품 구매 |
| 404 | ORDER-E002 | 상품 없음 또는 비공개 |
| 422 | ORDER-E004 | 구독 전용 상품 구매 시도 |
| 402 | ORDER-E003 | 결제 실패 |

---

### 5.2 구매 내역 조회

| 항목 | 내용 |
|---|---|
| Method | `GET` |
| URL | `/orders` |
| 인증 필요 | Bearer Token |

**쿼리 파라미터**

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| page | Integer | 0 | 페이지 번호 |
| size | Integer | 20 | 페이지당 항목 수 |
| startDate | String | - | 조회 시작일 (yyyy-MM-dd) |
| endDate | String | - | 조회 종료일 (yyyy-MM-dd) |

**응답 바디 (200)**: 페이지네이션 포맷, 항목 내 orderId / itemTitle / amount / paidAt / status

---

### 5.3 구매 취소 / 환불

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/orders/{orderId}/cancel` |
| 인증 필요 | Bearer Token (본인만) |

**요청 바디**

```json
{
  "reason": "단순 변심"
}
```

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "orderId": 20001,
    "status": "REFUNDED",
    "refundAmount": 15000,
    "refundedAt": "2026-05-09T13:00:00Z"
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 422 | ORDER-E010 | 환불 기간(7일) 초과 |
| 422 | ORDER-E011 | 콘텐츠 열람 이력 존재 |

---

## 6. 구독 API

### 6.1 구독 신청

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/subscriptions` |
| 인증 필요 | Bearer Token |

**요청 바디**

```json
{
  "itemId": 5001,
  "planId": 101,
  "paymentMethod": "CARD"
}
```

**응답 바디 (201)**

```json
{
  "success": true,
  "data": {
    "subscriptionId": 30001,
    "itemId": 5001,
    "itemTitle": "포토샵 작업 템플릿 50종",
    "planName": "Basic",
    "period": "MONTHLY",
    "amount": 5000,
    "status": "ACTIVE",
    "startedAt": "2026-05-09T12:00:00Z",
    "nextBillingAt": "2026-06-09T12:00:00Z"
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 409 | SUB-E001 | 이미 활성 구독 중 |
| 422 | SUB-E002 | 본인 상품 구독 시도 |
| 422 | SUB-E003 | 구독 미지원 상품 |
| 402 | SUB-E004 | 결제 실패 |

---

### 6.2 구독 해지

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/subscriptions/{subscriptionId}/cancel` |
| 인증 필요 | Bearer Token (본인만) |

**요청 바디**: 없음

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "subscriptionId": 30001,
    "status": "CANCEL_REQUESTED",
    "cancelledAt": "2026-05-09T14:00:00Z",
    "activeUntil": "2026-06-09T11:59:59Z"
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

---

### 6.3 구독 해지 취소 (재활성화)

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/subscriptions/{subscriptionId}/reactivate` |
| 인증 필요 | Bearer Token (본인만) |

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "subscriptionId": 30001,
    "status": "ACTIVE"
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

---

### 6.4 구독 내역 조회

| 항목 | 내용 |
|---|---|
| Method | `GET` |
| URL | `/subscriptions` |
| 인증 필요 | Bearer Token |

**쿼리 파라미터**

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| status | String | ALL | `ACTIVE` / `CANCEL_REQUESTED` / `CANCELLED` / `ALL` |
| page | Integer | 0 | 페이지 번호 |
| size | Integer | 20 | 페이지당 항목 수 |

**응답 바디 (200)**: 페이지네이션 포맷, 항목 내 subscriptionId / itemTitle / planName / amount / status / nextBillingAt / activeUntil

---

## 7. 사용자 프로필 API

### 7.1 셀러 공개 프로필 조회

| 항목 | 내용 |
|---|---|
| Method | `GET` |
| URL | `/users/{nickname}/profile` |
| 인증 필요 | 없음 |

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "userId": 1001,
    "nickname": "shelfy_user",
    "bio": "안녕하세요, 디자인 리소스를 공유합니다.",
    "profileImageUrl": "https://cdn.shelfy.io/profiles/1001.jpg",
    "itemCount": 12,
    "subscriberCount": 85,
    "joinedAt": "2025-01-15T00:00:00Z",
    "items": {
      "content": [ ... ],
      "page": 0,
      "size": 12,
      "totalElements": 12
    }
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

---

### 7.2 내 프로필 조회

| 항목 | 내용 |
|---|---|
| Method | `GET` |
| URL | `/users/me` |
| 인증 필요 | Bearer Token |

**응답 바디 (200)**: 공개 프로필 정보 + `email` / `emailVerified` / `agreeMarketing` / `createdAt`

---

### 7.3 내 프로필 수정

| 항목 | 내용 |
|---|---|
| Method | `PATCH` |
| URL | `/users/me` |
| 인증 필요 | Bearer Token |
| Content-Type | `application/json` |

**요청 바디** (변경할 필드만 포함)

```json
{
  "nickname": "new_nickname",
  "bio": "새로운 소개 문구",
  "profileImageId": "img-uuid-profile-001"
}
```

**응답 바디 (200)**: 수정된 프로필 정보

---

### 7.4 셀러 수익 현황 조회

| 항목 | 내용 |
|---|---|
| Method | `GET` |
| URL | `/users/me/revenue` |
| 인증 필요 | Bearer Token |

**쿼리 파라미터**

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| year | Integer | 현재 연도 | 조회 연도 |

**응답 바디 (200)**

```json
{
  "success": true,
  "data": {
    "totalRevenue": 1250000,
    "totalFee": 125000,
    "netRevenue": 1125000,
    "activeSubscribers": 85,
    "monthlyRevenue": [
      { "month": "2026-01", "revenue": 120000 },
      { "month": "2026-02", "revenue": 180000 }
    ],
    "itemRevenue": [
      {
        "itemId": 5001,
        "itemTitle": "포토샵 작업 템플릿 50종",
        "purchaseCount": 30,
        "subscriptionCount": 15,
        "revenue": 500000
      }
    ]
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

---

## 8. 파일 업로드 API

### 8.1 이미지 업로드

| 항목 | 내용 |
|---|---|
| Method | `POST` |
| URL | `/files/upload` |
| 인증 필요 | Bearer Token |
| Content-Type | `multipart/form-data` |

**요청 폼 데이터**

| 필드명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| file | File | Y | 업로드할 이미지 파일 (JPG/PNG/WEBP, 최대 10MB) |
| type | String | Y | `ITEM_IMAGE` / `PROFILE_IMAGE` |

**응답 바디 (201)**

```json
{
  "success": true,
  "data": {
    "imageId": "img-uuid-001",
    "url": "https://cdn.shelfy.io/images/img-uuid-001.jpg",
    "fileName": "template-preview.jpg",
    "fileSize": 2048576,
    "uploadedAt": "2026-05-09T12:00:00Z"
  },
  "error": null,
  "timestamp": "2026-05-09T12:00:00Z"
}
```

**에러 케이스**

| HTTP | 에러 코드 | 상황 |
|---|---|---|
| 400 | ITEM-E002 | 지원하지 않는 파일 형식 |
| 400 | ITEM-E003 | 파일 용량 초과 (10MB) |

---

## Appendix. API 엔드포인트 요약

| Method | URL | 기능 | 인증 |
|---|---|---|---|
| POST | /auth/signup | 회원가입 | 없음 |
| GET | /auth/verify-email | 이메일 인증 | 없음 |
| POST | /auth/resend-verification | 인증 메일 재발송 | 없음 |
| POST | /auth/login | 로그인 | 없음 |
| POST | /auth/logout | 로그아웃 | Bearer |
| POST | /auth/token/refresh | 토큰 갱신 | Cookie |
| POST | /auth/forgot-password | 비밀번호 재설정 요청 | 없음 |
| POST | /auth/reset-password | 비밀번호 재설정 | 없음 |
| DELETE | /auth/me | 회원 탈퇴 | Bearer |
| POST | /items | 상품 등록 | Bearer |
| GET | /items | 상품 목록 탐색 | 없음 |
| GET | /items/search | 상품 검색 | 없음 |
| GET | /items/my | 내 상품 목록 | Bearer |
| GET | /items/{itemId} | 상품 상세 조회 | 없음 |
| PUT | /items/{itemId} | 상품 수정 | Bearer |
| DELETE | /items/{itemId} | 상품 삭제 | Bearer |
| PATCH | /items/{itemId}/status | 상품 상태 변경 | Bearer |
| POST | /orders | 구매 주문 생성 | Bearer |
| GET | /orders | 구매 내역 조회 | Bearer |
| POST | /orders/{orderId}/cancel | 구매 취소/환불 | Bearer |
| POST | /subscriptions | 구독 신청 | Bearer |
| GET | /subscriptions | 구독 내역 조회 | Bearer |
| POST | /subscriptions/{id}/cancel | 구독 해지 | Bearer |
| POST | /subscriptions/{id}/reactivate | 구독 해지 취소 | Bearer |
| GET | /users/{nickname}/profile | 셀러 공개 프로필 | 없음 |
| GET | /users/me | 내 프로필 조회 | Bearer |
| PATCH | /users/me | 내 프로필 수정 | Bearer |
| GET | /users/me/revenue | 수익 현황 조회 | Bearer |
| POST | /files/upload | 이미지 업로드 | Bearer |
