# API 요구사항 정의서

- **프로젝트명**: 발자국 (Foot-Print)
- **문서 버전**: v1.0.0
- **작성일**: 2026-05-09
- **작성자**: Planner
- **상태**: 초안 (Draft)

---

## 목차

1. [공통 규약](#1-공통-규약)
2. [인증 방식](#2-인증-방식)
3. [공통 요청/응답 포맷](#3-공통-요청응답-포맷)
4. [공통 에러 코드](#4-공통-에러-코드)
5. [API 목록](#5-api-목록)
6. [API 상세 명세](#6-api-상세-명세)
   - [6.1 인증 (Auth)](#61-인증-auth)
   - [6.2 장소 (Place)](#62-장소-place)
   - [6.3 장소 사진 (Place Photo)](#63-장소-사진-place-photo)
   - [6.4 카테고리 (Category)](#64-카테고리-category)
   - [6.5 통계 (Statistics)](#65-통계-statistics)
   - [6.6 사용자 (User)](#66-사용자-user)
   - [6.7 시스템 (System)](#67-시스템-system)

---

## 1. 공통 규약

### 1.1 Base URL

```
개발 환경: http://localhost:8080/api/v1
운영 환경: https://api.footprint.example.com/api/v1
```

### 1.2 URL 설계 원칙

| 원칙 | 예시 |
|------|------|
| 리소스는 복수 명사 사용 | `/places`, `/categories` |
| 계층 구조는 경로로 표현 | `/places/{placeId}/photos` |
| API 버전은 URL에 포함 | `/api/v1/...` |
| 동작은 HTTP Method로 표현 | GET(조회), POST(생성), PUT(전체 수정), PATCH(부분 수정), DELETE(삭제) |
| 소문자 및 하이픈 사용 | `/place-records` (단어 구분 시) |

### 1.3 HTTP Method 사용 기준

| Method | 용도 | 멱등성 |
|--------|------|--------|
| GET | 리소스 조회 | 멱등 |
| POST | 리소스 생성, 복잡한 조회(검색) | 비멱등 |
| PUT | 리소스 전체 수정 | 멱등 |
| PATCH | 리소스 부분 수정 | 비멱등 |
| DELETE | 리소스 삭제 | 멱등 |

### 1.4 Content-Type

| 구분 | Content-Type |
|------|-------------|
| 일반 요청 | `application/json` |
| 파일 업로드 요청 | `multipart/form-data` |
| 응답 | `application/json; charset=UTF-8` |

---

## 2. 인증 방식

### 2.1 JWT Bearer Token

모든 API (인증 관련 API 제외)는 요청 헤더에 Access Token을 포함해야 한다.

```http
Authorization: Bearer {accessToken}
```

### 2.2 토큰 규격

| 토큰 종류 | 유효 기간 | 저장 위치 |
|-----------|----------|----------|
| Access Token | 30분 | 메모리 (또는 HttpOnly Cookie - DevLead 확정) |
| Refresh Token | 7일 | HttpOnly Cookie (`refresh_token`) |

### 2.3 토큰 갱신 흐름

```
1. 클라이언트 → API 호출 (Access Token 포함)
2. 서버 → 401 TOKEN_EXPIRED 응답
3. 클라이언트 → POST /api/v1/auth/refresh (Refresh Token 쿠키 자동 포함)
4. 서버 → 신규 Access Token 발급
5. 클라이언트 → 원래 API 재호출
6. Refresh Token 만료 시 → 401 REFRESH_TOKEN_EXPIRED → 로그인 화면 강제 이동
```

### 2.4 인증 불필요 엔드포인트

| URL | Method | 설명 |
|-----|--------|------|
| `/api/v1/auth/login` | POST | 로그인 |
| `/api/v1/auth/register` | POST | 회원가입 |
| `/api/v1/auth/refresh` | POST | 토큰 갱신 |
| `/api/v1/health` | GET | 헬스체크 |

---

## 3. 공통 요청/응답 포맷

### 3.1 공통 응답 포맷 (성공)

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "요청이 성공적으로 처리되었습니다.",
  "data": { /* 응답 데이터 */ },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

### 3.2 공통 응답 포맷 (실패)

```json
{
  "success": false,
  "code": "ERROR_CODE",
  "message": "오류 메시지",
  "errors": [
    {
      "field": "email",
      "message": "올바른 이메일 형식을 입력해 주세요."
    }
  ],
  "timestamp": "2026-05-09T10:00:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `success` | Boolean | 처리 성공 여부 |
| `code` | String | 결과 코드 (성공: `SUCCESS`, 실패: 오류 코드) |
| `message` | String | 결과 메시지 |
| `data` | Object / Array / null | 응답 데이터 (실패 시 null) |
| `errors` | Array / null | 유효성 오류 상세 (성공 시 null) |
| `timestamp` | String (ISO 8601) | 응답 시각 |

### 3.3 페이지네이션 응답 포맷

목록 조회 API의 `data` 구조:

```json
{
  "content": [ /* 항목 배열 */ ],
  "page": {
    "number": 0,
    "size": 20,
    "totalElements": 42,
    "totalPages": 3,
    "first": true,
    "last": false
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `content` | Array | 현재 페이지 항목 배열 |
| `page.number` | Integer | 현재 페이지 번호 (0부터 시작) |
| `page.size` | Integer | 페이지당 항목 수 |
| `page.totalElements` | Integer | 전체 항목 수 |
| `page.totalPages` | Integer | 전체 페이지 수 |
| `page.first` | Boolean | 첫 페이지 여부 |
| `page.last` | Boolean | 마지막 페이지 여부 |

### 3.4 공통 쿼리 파라미터 (목록 조회)

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `page` | Integer | 0 | 페이지 번호 (0부터 시작) |
| `size` | Integer | 20 | 페이지당 항목 수 (최대 100) |
| `sort` | String | `visitedAt,desc` | 정렬 기준 (필드명,방향) |

---

## 4. 공통 에러 코드

| HTTP Status | 에러 코드 | 설명 |
|-------------|----------|------|
| 400 | `INVALID_INPUT` | 요청 파라미터 유효성 실패 |
| 400 | `INVALID_EMAIL` | 이메일 형식 오류 |
| 400 | `WEAK_PASSWORD` | 비밀번호 강도 미달 |
| 400 | `PASSWORD_MISMATCH` | 비밀번호 확인 불일치 |
| 400 | `FUTURE_DATE` | 미래 날짜 입력 오류 |
| 400 | `INVALID_COORDINATE` | 유효하지 않은 좌표값 |
| 401 | `UNAUTHORIZED` | 미인증 요청 |
| 401 | `TOKEN_EXPIRED` | Access Token 만료 |
| 401 | `REFRESH_TOKEN_EXPIRED` | Refresh Token 만료 |
| 401 | `AUTH_FAILED` | 이메일/비밀번호 불일치 |
| 403 | `FORBIDDEN` | 접근 권한 없음 (타인 데이터) |
| 404 | `NOT_FOUND` | 리소스 없음 |
| 404 | `PLACE_NOT_FOUND` | 장소 없음 |
| 404 | `CATEGORY_NOT_FOUND` | 카테고리 없음 |
| 409 | `EMAIL_DUPLICATED` | 이메일 중복 |
| 409 | `CATEGORY_NAME_DUPLICATED` | 카테고리명 중복 |
| 409 | `CATEGORY_IN_USE` | 사용 중인 카테고리 삭제 불가 |
| 413 | `FILE_TOO_LARGE` | 파일 크기 초과 (최대 10MB) |
| 413 | `PHOTO_LIMIT_EXCEEDED` | 사진 최대 개수(5장) 초과 |
| 413 | `CATEGORY_LIMIT_EXCEEDED` | 카테고리 최대 개수(20개) 초과 |
| 415 | `UNSUPPORTED_FILE_TYPE` | 허용되지 않는 파일 형식 |
| 429 | `TOO_MANY_REQUESTS` | Rate Limit 초과 |
| 500 | `SERVER_ERROR` | 서버 내부 오류 |

---

## 5. API 목록

### 인증 (Auth)

| # | Method | URL | 설명 | 인증 필요 |
|---|--------|-----|------|----------|
| A-01 | POST | `/auth/register` | 회원가입 | N |
| A-02 | POST | `/auth/login` | 로그인 | N |
| A-03 | POST | `/auth/logout` | 로그아웃 | Y |
| A-04 | POST | `/auth/refresh` | Access Token 갱신 | N (Refresh Token 쿠키) |
| A-05 | DELETE | `/auth/withdraw` | 회원 탈퇴 | Y |

### 장소 (Place)

| # | Method | URL | 설명 | 인증 필요 |
|---|--------|-----|------|----------|
| P-01 | GET | `/places` | 장소 목록 조회 (검색/필터 포함) | Y |
| P-02 | POST | `/places` | 장소 등록 | Y |
| P-03 | GET | `/places/{placeId}` | 장소 상세 조회 | Y |
| P-04 | PUT | `/places/{placeId}` | 장소 수정 | Y |
| P-05 | DELETE | `/places/{placeId}` | 장소 삭제 | Y |

### 장소 사진 (Place Photo)

| # | Method | URL | 설명 | 인증 필요 |
|---|--------|-----|------|----------|
| PH-01 | POST | `/places/{placeId}/photos` | 사진 업로드 | Y |
| PH-02 | DELETE | `/places/{placeId}/photos/{photoId}` | 사진 삭제 | Y |

### 카테고리 (Category)

| # | Method | URL | 설명 | 인증 필요 |
|---|--------|-----|------|----------|
| C-01 | GET | `/categories` | 카테고리 목록 조회 | Y |
| C-02 | POST | `/categories` | 카테고리 생성 | Y |
| C-03 | PUT | `/categories/{categoryId}` | 카테고리 수정 | Y |
| C-04 | DELETE | `/categories/{categoryId}` | 카테고리 삭제 | Y |

### 통계 (Statistics)

| # | Method | URL | 설명 | 인증 필요 |
|---|--------|-----|------|----------|
| S-01 | GET | `/stats/summary` | 요약 통계 조회 | Y |
| S-02 | GET | `/stats/monthly` | 월별 방문 수 통계 | Y |
| S-03 | GET | `/stats/category` | 카테고리별 분포 통계 | Y |
| S-04 | GET | `/stats/region` | 지역별 방문 통계 | Y |

### 사용자 (User)

| # | Method | URL | 설명 | 인증 필요 |
|---|--------|-----|------|----------|
| U-01 | GET | `/users/me` | 내 프로필 조회 | Y |
| U-02 | PATCH | `/users/me` | 프로필 수정 (닉네임) | Y |
| U-03 | POST | `/users/me/profile-image` | 프로필 사진 변경 | Y |
| U-04 | PATCH | `/users/me/password` | 비밀번호 변경 | Y |

### 시스템 (System)

| # | Method | URL | 설명 | 인증 필요 |
|---|--------|-----|------|----------|
| SYS-01 | GET | `/health` | 헬스체크 | N |

---

## 6. API 상세 명세

---

### 6.1 인증 (Auth)

---

#### A-01: 회원가입

```
POST /api/v1/auth/register
Content-Type: application/json
```

**요청 Body**

```json
{
  "email": "user@example.com",
  "password": "Password1!",
  "passwordConfirm": "Password1!",
  "nickname": "홍길동"
}
```

| 필드 | 타입 | 필수 | 유효성 규칙 |
|------|------|------|------------|
| `email` | String | Y | 이메일 형식, 최대 255자 |
| `password` | String | Y | 8~20자, 영문+숫자+특수문자 각 1자 이상 |
| `passwordConfirm` | String | Y | `password`와 동일값 |
| `nickname` | String | Y | 2~20자 |

**응답 (201 Created)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "회원가입이 완료되었습니다.",
  "data": {
    "userId": "uuid-string",
    "email": "user@example.com",
    "nickname": "홍길동"
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 이메일 형식 오류 | 400 | `INVALID_EMAIL` |
| 비밀번호 강도 미달 | 400 | `WEAK_PASSWORD` |
| 비밀번호 확인 불일치 | 400 | `INVALID_INPUT` |
| 이메일 중복 | 409 | `EMAIL_DUPLICATED` |

---

#### A-02: 로그인

```
POST /api/v1/auth/login
Content-Type: application/json
```

**요청 Body**

```json
{
  "email": "user@example.com",
  "password": "Password1!"
}
```

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "로그인이 완료되었습니다.",
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiJ9...",
    "tokenType": "Bearer",
    "expiresIn": 1800,
    "user": {
      "userId": "uuid-string",
      "email": "user@example.com",
      "nickname": "홍길동",
      "profileImageUrl": "https://cdn.example.com/profiles/uuid.jpg"
    }
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

응답 헤더:
```
Set-Cookie: refresh_token={refreshToken}; HttpOnly; Secure; SameSite=Strict; Max-Age=604800; Path=/api/v1/auth
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 이메일/비밀번호 불일치 | 401 | `AUTH_FAILED` |
| 이메일 형식 오류 | 400 | `INVALID_EMAIL` |

---

#### A-03: 로그아웃

```
POST /api/v1/auth/logout
Authorization: Bearer {accessToken}
```

**요청 Body**: 없음

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "로그아웃되었습니다.",
  "data": null,
  "timestamp": "2026-05-09T10:00:00Z"
}
```

응답 헤더:
```
Set-Cookie: refresh_token=; HttpOnly; Max-Age=0; Path=/api/v1/auth
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 미인증 요청 | 401 | `UNAUTHORIZED` |

---

#### A-04: Access Token 갱신

```
POST /api/v1/auth/refresh
Cookie: refresh_token={refreshToken}
```

**요청 Body**: 없음

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "토큰이 갱신되었습니다.",
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiJ9...",
    "tokenType": "Bearer",
    "expiresIn": 1800
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| Refresh Token 없음 | 401 | `UNAUTHORIZED` |
| Refresh Token 만료 | 401 | `REFRESH_TOKEN_EXPIRED` |
| Refresh Token 위변조 | 401 | `UNAUTHORIZED` |

---

#### A-05: 회원 탈퇴

```
DELETE /api/v1/auth/withdraw
Authorization: Bearer {accessToken}
Content-Type: application/json
```

**요청 Body**

```json
{
  "password": "Password1!"
}
```

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "회원 탈퇴가 완료되었습니다.",
  "data": null,
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 비밀번호 불일치 | 401 | `AUTH_FAILED` |
| 미인증 요청 | 401 | `UNAUTHORIZED` |

---

### 6.2 장소 (Place)

---

#### P-01: 장소 목록 조회

```
GET /api/v1/places
Authorization: Bearer {accessToken}
```

**쿼리 파라미터**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `page` | Integer | N | 0 | 페이지 번호 |
| `size` | Integer | N | 20 | 페이지당 항목 수 (최대 100) |
| `sort` | String | N | `visitedAt,desc` | 정렬 기준 (visitedAt, createdAt, rating) |
| `keyword` | String | N | - | 검색 키워드 (장소명, 주소, 메모, 태그) |
| `categoryIds` | Integer[] | N | - | 카테고리 ID 목록 (다중 선택, 쉼표 구분) |
| `visitedFrom` | String | N | - | 방문일 시작 (YYYY-MM-DD) |
| `visitedTo` | String | N | - | 방문일 종료 (YYYY-MM-DD) |
| `minRating` | Integer | N | - | 최소 평점 (1~5) |
| `tags` | String[] | N | - | 태그 목록 (다중 선택, 쉼표 구분) |
| `view` | String | N | `list` | 조회 모드: `list`(페이지네이션), `map`(전체) |

> `view=map` 일 때: 페이지네이션 미적용, 전체 장소 반환 (지도용 경량 응답 - 좌표/장소명/카테고리만 포함)

**응답 (200 OK) - view=list**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "요청이 성공적으로 처리되었습니다.",
  "data": {
    "content": [
      {
        "placeId": 1,
        "name": "을지로 순대국",
        "address": "서울 중구 을지로 123",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "visitedAt": "2026-04-15",
        "rating": 4,
        "memo": "국물이 진하고 맛있다...",
        "thumbnailUrl": "https://cdn.example.com/photos/uuid.jpg",
        "categories": [
          { "categoryId": 1, "name": "맛집", "color": "#FF6B6B", "isDefault": true }
        ],
        "tags": ["혼밥", "순대국", "을지로"],
        "createdAt": "2026-04-16T10:00:00Z"
      }
    ],
    "page": {
      "number": 0,
      "size": 20,
      "totalElements": 42,
      "totalPages": 3,
      "first": true,
      "last": false
    }
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**응답 (200 OK) - view=map**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "요청이 성공적으로 처리되었습니다.",
  "data": [
    {
      "placeId": 1,
      "name": "을지로 순대국",
      "latitude": 37.5665,
      "longitude": 126.9780,
      "visitedAt": "2026-04-15",
      "thumbnailUrl": "https://cdn.example.com/photos/uuid.jpg",
      "categories": [
        { "categoryId": 1, "name": "맛집", "color": "#FF6B6B" }
      ]
    }
  ],
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 미인증 요청 | 401 | `UNAUTHORIZED` |
| 잘못된 날짜 형식 | 400 | `INVALID_INPUT` |
| 잘못된 평점 범위 | 400 | `INVALID_INPUT` |

---

#### P-02: 장소 등록

```
POST /api/v1/places
Authorization: Bearer {accessToken}
Content-Type: application/json
```

**요청 Body**

```json
{
  "name": "을지로 순대국",
  "categoryIds": [1, 5],
  "visitedAt": "2026-04-15",
  "latitude": 37.5665,
  "longitude": 126.9780,
  "address": "서울 중구 을지로 123",
  "memo": "국물이 진하고 맛있다. 반찬도 푸짐함.",
  "rating": 4,
  "tags": ["혼밥", "순대국", "을지로"]
}
```

| 필드 | 타입 | 필수 | 유효성 규칙 |
|------|------|------|------------|
| `name` | String | Y | 1~100자 |
| `categoryIds` | Integer[] | Y | 1개 이상, 존재하는 카테고리 ID |
| `visitedAt` | String | Y | YYYY-MM-DD, 오늘 이하 |
| `latitude` | Double | Y | -90.0 ~ 90.0 |
| `longitude` | Double | Y | -180.0 ~ 180.0 |
| `address` | String | N | 최대 255자 |
| `memo` | String | N | 최대 2,000자 |
| `rating` | Integer | N | 1~5 |
| `tags` | String[] | N | 각 태그 최대 20자, 최대 10개 |

**응답 (201 Created)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "장소가 등록되었습니다.",
  "data": {
    "placeId": 43,
    "name": "을지로 순대국",
    "address": "서울 중구 을지로 123",
    "latitude": 37.5665,
    "longitude": 126.9780,
    "visitedAt": "2026-04-15",
    "rating": 4,
    "memo": "국물이 진하고 맛있다. 반찬도 푸짐함.",
    "photos": [],
    "categories": [
      { "categoryId": 1, "name": "맛집", "color": "#FF6B6B", "isDefault": true }
    ],
    "tags": ["혼밥", "순대국", "을지로"],
    "createdAt": "2026-05-09T10:00:00Z",
    "updatedAt": "2026-05-09T10:00:00Z"
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 필수 필드 누락 | 400 | `INVALID_INPUT` |
| 미래 날짜 입력 | 400 | `FUTURE_DATE` |
| 좌표 범위 초과 | 400 | `INVALID_COORDINATE` |
| 존재하지 않는 카테고리 ID | 404 | `CATEGORY_NOT_FOUND` |
| 미인증 요청 | 401 | `UNAUTHORIZED` |

---

#### P-03: 장소 상세 조회

```
GET /api/v1/places/{placeId}
Authorization: Bearer {accessToken}
```

**경로 파라미터**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `placeId` | Long | Y | 장소 ID |

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "요청이 성공적으로 처리되었습니다.",
  "data": {
    "placeId": 43,
    "name": "을지로 순대국",
    "address": "서울 중구 을지로 123",
    "latitude": 37.5665,
    "longitude": 126.9780,
    "visitedAt": "2026-04-15",
    "rating": 4,
    "memo": "국물이 진하고 맛있다. 반찬도 푸짐함.",
    "photos": [
      {
        "photoId": 1,
        "url": "https://cdn.example.com/photos/uuid1.jpg",
        "thumbnailUrl": "https://cdn.example.com/photos/thumb_uuid1.jpg",
        "order": 1
      }
    ],
    "categories": [
      { "categoryId": 1, "name": "맛집", "color": "#FF6B6B", "isDefault": true }
    ],
    "tags": ["혼밥", "순대국", "을지로"],
    "createdAt": "2026-05-09T10:00:00Z",
    "updatedAt": "2026-05-09T10:00:00Z"
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 장소 없음 | 404 | `PLACE_NOT_FOUND` |
| 타인 장소 접근 | 403 | `FORBIDDEN` |
| 미인증 요청 | 401 | `UNAUTHORIZED` |

---

#### P-04: 장소 수정

```
PUT /api/v1/places/{placeId}
Authorization: Bearer {accessToken}
Content-Type: application/json
```

**경로 파라미터**: `placeId` (Long, 필수)

**요청 Body**: P-02 등록과 동일한 구조 (전체 필드 전송)

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "장소가 수정되었습니다.",
  "data": { /* P-03 상세 조회 응답 data와 동일 */ },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 장소 없음 | 404 | `PLACE_NOT_FOUND` |
| 타인 장소 수정 | 403 | `FORBIDDEN` |
| 미인증 요청 | 401 | `UNAUTHORIZED` |
| 미래 날짜 입력 | 400 | `FUTURE_DATE` |

---

#### P-05: 장소 삭제

```
DELETE /api/v1/places/{placeId}
Authorization: Bearer {accessToken}
```

**경로 파라미터**: `placeId` (Long, 필수)

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "장소가 삭제되었습니다.",
  "data": null,
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 장소 없음 | 404 | `PLACE_NOT_FOUND` |
| 타인 장소 삭제 | 403 | `FORBIDDEN` |
| 미인증 요청 | 401 | `UNAUTHORIZED` |

---

### 6.3 장소 사진 (Place Photo)

---

#### PH-01: 사진 업로드

```
POST /api/v1/places/{placeId}/photos
Authorization: Bearer {accessToken}
Content-Type: multipart/form-data
```

**경로 파라미터**: `placeId` (Long, 필수)

**요청 Form Data**

| 필드 | 타입 | 필수 | 유효성 규칙 |
|------|------|------|------------|
| `photos` | File[] | Y | JPG/PNG/WebP, 장당 최대 10MB, 최대 5장 (기존 사진 합산) |

**응답 (201 Created)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "사진이 업로드되었습니다.",
  "data": [
    {
      "photoId": 1,
      "url": "https://cdn.example.com/photos/uuid1.jpg",
      "thumbnailUrl": "https://cdn.example.com/photos/thumb_uuid1.jpg",
      "order": 1
    }
  ],
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 사진 개수 초과 | 413 | `PHOTO_LIMIT_EXCEEDED` |
| 파일 크기 초과 | 413 | `FILE_TOO_LARGE` |
| 허용되지 않는 파일 타입 | 415 | `UNSUPPORTED_FILE_TYPE` |
| 장소 없음 | 404 | `PLACE_NOT_FOUND` |
| 타인 장소 접근 | 403 | `FORBIDDEN` |

---

#### PH-02: 사진 삭제

```
DELETE /api/v1/places/{placeId}/photos/{photoId}
Authorization: Bearer {accessToken}
```

**경로 파라미터**

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `placeId` | Long | 장소 ID |
| `photoId` | Long | 사진 ID |

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "사진이 삭제되었습니다.",
  "data": null,
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 장소 또는 사진 없음 | 404 | `NOT_FOUND` |
| 타인 장소 접근 | 403 | `FORBIDDEN` |

---

### 6.4 카테고리 (Category)

---

#### C-01: 카테고리 목록 조회

```
GET /api/v1/categories
Authorization: Bearer {accessToken}
```

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "요청이 성공적으로 처리되었습니다.",
  "data": {
    "defaultCategories": [
      {
        "categoryId": 1,
        "name": "맛집",
        "color": "#FF6B6B",
        "icon": "restaurant",
        "isDefault": true,
        "placeCount": 12
      }
    ],
    "userCategories": [
      {
        "categoryId": 10,
        "name": "산책코스",
        "color": "#4CAF50",
        "icon": "walk",
        "isDefault": false,
        "placeCount": 4
      }
    ],
    "totalCount": 11,
    "limitCount": 20
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

---

#### C-02: 카테고리 생성

```
POST /api/v1/categories
Authorization: Bearer {accessToken}
Content-Type: application/json
```

**요청 Body**

```json
{
  "name": "산책코스",
  "color": "#4CAF50",
  "icon": "walk"
}
```

| 필드 | 타입 | 필수 | 유효성 규칙 |
|------|------|------|------------|
| `name` | String | Y | 1~20자, 동일 사용자 내 중복 불가 |
| `color` | String | N | `#RRGGBB` 형식, 미입력 시 기본값 적용 |
| `icon` | String | N | 허용 아이콘 코드 목록 중 선택 |

**응답 (201 Created)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "카테고리가 생성되었습니다.",
  "data": {
    "categoryId": 10,
    "name": "산책코스",
    "color": "#4CAF50",
    "icon": "walk",
    "isDefault": false,
    "placeCount": 0
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 카테고리명 중복 | 409 | `CATEGORY_NAME_DUPLICATED` |
| 카테고리 최대 개수 초과 | 413 | `CATEGORY_LIMIT_EXCEEDED` |
| 미인증 요청 | 401 | `UNAUTHORIZED` |

---

#### C-03: 카테고리 수정

```
PUT /api/v1/categories/{categoryId}
Authorization: Bearer {accessToken}
Content-Type: application/json
```

**경로 파라미터**: `categoryId` (Long, 필수)

**요청 Body**: C-02 생성과 동일한 구조

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "카테고리가 수정되었습니다.",
  "data": {
    "categoryId": 10,
    "name": "산책코스",
    "color": "#4CAF50",
    "icon": "walk",
    "isDefault": false,
    "placeCount": 4
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 기본 카테고리 수정 시도 | 403 | `FORBIDDEN` |
| 카테고리 없음 | 404 | `CATEGORY_NOT_FOUND` |
| 타인 카테고리 접근 | 403 | `FORBIDDEN` |
| 카테고리명 중복 | 409 | `CATEGORY_NAME_DUPLICATED` |

---

#### C-04: 카테고리 삭제

```
DELETE /api/v1/categories/{categoryId}
Authorization: Bearer {accessToken}
```

**경로 파라미터**: `categoryId` (Long, 필수)

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "카테고리가 삭제되었습니다.",
  "data": null,
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 기본 카테고리 삭제 시도 | 403 | `FORBIDDEN` |
| 카테고리 없음 | 404 | `CATEGORY_NOT_FOUND` |
| 타인 카테고리 접근 | 403 | `FORBIDDEN` |
| 사용 중인 카테고리 | 409 | `CATEGORY_IN_USE` |

---

### 6.5 통계 (Statistics)

---

#### S-01: 요약 통계 조회

```
GET /api/v1/stats/summary
Authorization: Bearer {accessToken}
```

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "요청이 성공적으로 처리되었습니다.",
  "data": {
    "totalPlaces": 42,
    "thisMonthPlaces": 5,
    "totalCategories": 11,
    "topCategory": {
      "categoryId": 1,
      "name": "맛집",
      "placeCount": 12
    }
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

---

#### S-02: 월별 방문 수 통계

```
GET /api/v1/stats/monthly
Authorization: Bearer {accessToken}
```

**쿼리 파라미터**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `months` | Integer | N | 12 | 조회 기간 (최근 N개월, 최대 24) |

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "요청이 성공적으로 처리되었습니다.",
  "data": [
    { "year": 2025, "month": 6, "count": 3 },
    { "year": 2025, "month": 7, "count": 5 },
    { "year": 2026, "month": 5, "count": 5 }
  ],
  "timestamp": "2026-05-09T10:00:00Z"
}
```

---

#### S-03: 카테고리별 분포 통계

```
GET /api/v1/stats/category
Authorization: Bearer {accessToken}
```

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "요청이 성공적으로 처리되었습니다.",
  "data": [
    {
      "categoryId": 1,
      "name": "맛집",
      "color": "#FF6B6B",
      "count": 12,
      "ratio": 28.6
    }
  ],
  "timestamp": "2026-05-09T10:00:00Z"
}
```

---

#### S-04: 지역별 방문 통계

```
GET /api/v1/stats/region
Authorization: Bearer {accessToken}
```

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "요청이 성공적으로 처리되었습니다.",
  "data": [
    { "region": "서울", "count": 28, "ratio": 66.7 },
    { "region": "경기", "count": 8, "ratio": 19.0 },
    { "region": "부산", "count": 4, "ratio": 9.5 }
  ],
  "timestamp": "2026-05-09T10:00:00Z"
}
```

---

### 6.6 사용자 (User)

---

#### U-01: 내 프로필 조회

```
GET /api/v1/users/me
Authorization: Bearer {accessToken}
```

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "요청이 성공적으로 처리되었습니다.",
  "data": {
    "userId": "uuid-string",
    "email": "user@example.com",
    "nickname": "홍길동",
    "profileImageUrl": "https://cdn.example.com/profiles/uuid.jpg",
    "createdAt": "2026-01-01T00:00:00Z"
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

---

#### U-02: 프로필 수정 (닉네임)

```
PATCH /api/v1/users/me
Authorization: Bearer {accessToken}
Content-Type: application/json
```

**요청 Body**

```json
{
  "nickname": "새닉네임"
}
```

| 필드 | 타입 | 필수 | 유효성 규칙 |
|------|------|------|------------|
| `nickname` | String | Y | 2~20자 |

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "프로필이 수정되었습니다.",
  "data": {
    "userId": "uuid-string",
    "email": "user@example.com",
    "nickname": "새닉네임",
    "profileImageUrl": "https://cdn.example.com/profiles/uuid.jpg"
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

---

#### U-03: 프로필 사진 변경

```
POST /api/v1/users/me/profile-image
Authorization: Bearer {accessToken}
Content-Type: multipart/form-data
```

**요청 Form Data**

| 필드 | 타입 | 필수 | 유효성 규칙 |
|------|------|------|------------|
| `image` | File | Y | JPG/PNG, 최대 2MB |

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "프로필 사진이 변경되었습니다.",
  "data": {
    "profileImageUrl": "https://cdn.example.com/profiles/new_uuid.jpg"
  },
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 파일 크기 초과 (2MB) | 413 | `FILE_TOO_LARGE` |
| 허용되지 않는 파일 타입 | 415 | `UNSUPPORTED_FILE_TYPE` |

---

#### U-04: 비밀번호 변경

```
PATCH /api/v1/users/me/password
Authorization: Bearer {accessToken}
Content-Type: application/json
```

**요청 Body**

```json
{
  "currentPassword": "OldPassword1!",
  "newPassword": "NewPassword2@",
  "newPasswordConfirm": "NewPassword2@"
}
```

| 필드 | 타입 | 필수 | 유효성 규칙 |
|------|------|------|------------|
| `currentPassword` | String | Y | 공백 불가 |
| `newPassword` | String | Y | 8~20자, 영문+숫자+특수문자 포함 |
| `newPasswordConfirm` | String | Y | `newPassword`와 동일 |

**응답 (200 OK)**

```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "비밀번호가 변경되었습니다.",
  "data": null,
  "timestamp": "2026-05-09T10:00:00Z"
}
```

**에러 케이스**

| 상황 | HTTP Status | 에러 코드 |
|------|-------------|----------|
| 현재 비밀번호 불일치 | 401 | `AUTH_FAILED` |
| 새 비밀번호 강도 미달 | 400 | `WEAK_PASSWORD` |
| 새 비밀번호 확인 불일치 | 400 | `PASSWORD_MISMATCH` |

---

### 6.7 시스템 (System)

---

#### SYS-01: 헬스체크

```
GET /api/v1/health
```

**응답 (200 OK)**

```json
{
  "status": "UP",
  "timestamp": "2026-05-09T10:00:00Z"
}
```

---

## 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| v1.0.0 | 2026-05-09 | Planner | 최초 작성 |

---

*문서 끝 - 본 문서의 변경 사항은 DevLead, BackendSenior, BackendDev, FrontendSenior에게 즉시 공유한다.*
