# Shelfy - 기술 아키텍처 설계서

- 작성일: 2026-05-09
- 작성자: DevLead
- 버전: v1.0.0

---

## 목차

1. [전체 시스템 아키텍처](#1-전체-시스템-아키텍처)
2. [Backend 패키지 구조](#2-backend-패키지-구조)
3. [Frontend 디렉토리 구조](#3-frontend-디렉토리-구조)
4. [인증 구조](#4-인증-구조)
5. [이미지 업로드 처리 방식](#5-이미지-업로드-처리-방식)
6. [Docker Compose 구성 개요](#6-docker-compose-구성-개요)
7. [기술 결정 사항 (ADR)](#7-기술-결정-사항-adr)

---

## 1. 전체 시스템 아키텍처

### 1.1 시스템 구성도 (ASCII)

```
                          [Internet]
                              |
                     [Reverse Proxy / Nginx]
                    /                       \
          [Frontend]                     [Backend API]
        Next.js 14 App                Spring Boot 3.x
        (SSR / CSR)                   Port: 8080
        Port: 3000                         |
              |                      [Spring Security]
              |                      [JWT Filter]
              |                            |
        [TanStack Query]           [Service Layer]
        (API 요청 캐시)                    |
              |                    [Repository Layer]
              \                   /MyBatis / JPA\
               \                 /               \
          [REST API - /api/v1]          [PostgreSQL 15]
                                        Port: 5432
                                              |
                                       [Volume Mount]

   [Object Storage / CDN]
   (이미지 파일 저장)
   - 로컬: MinIO (Docker)
   - 운영: Cloud Object Storage + CDN
```

### 1.2 네트워크 구성 (Docker 내부)

```
Docker Network: shelfy-network
+--------------------+     +--------------------+     +--------------------+
|    frontend        |     |    backend         |     |    postgres         |
|    (Next.js)       | --> |    (Spring Boot)   | --> |    (PostgreSQL 15)  |
|    Port: 3000      |     |    Port: 8080      |     |    Port: 5432       |
+--------------------+     +--------------------+     +--------------------+
                                     |
                           +--------------------+
                           |    minio           |
                           |    (Object Storage)|
                           |    Port: 9000      |
                           +--------------------+
```

### 1.3 요청 흐름

```
Client Browser
    |
    | 1. 페이지 요청 (SSR)
    v
Next.js Server (SSR)
    |
    | 2. 초기 데이터 fetch (Server Component)
    v
Spring Boot API (/api/v1/...)
    |
    | 3. JWT 검증 (Spring Security Filter)
    v
Service Layer (비즈니스 로직)
    |
    | 4. 데이터 조회/변경
    v
Repository (MyBatis / JPA)
    |
    v
PostgreSQL
    |
    | 5. 응답 반환
    v
Client (React Hydration)
    |
    | 6. 이후 CSR 인터랙션은 TanStack Query로 처리
    v
Spring Boot API (TanStack Query fetch)
```

---

## 2. Backend 패키지 구조

### 2.1 레이어드 아키텍처 원칙

```
Presentation Layer   : Controller (HTTP 요청/응답, DTO 변환)
Business Layer       : Service (비즈니스 로직, 트랜잭션 관리)
Persistence Layer    : Repository / Mapper (DB 접근)
Domain Layer         : Entity, Enum, Domain 객체
Infrastructure Layer : Config, Security, External 연동
```

### 2.2 패키지 구조

```
com.shelfy
├── ShelfyApplication.java
│
├── common/                          # 공통 모듈
│   ├── response/
│   │   ├── ApiResponse.java         # 공통 응답 래퍼
│   │   ├── PageResponse.java        # 페이지네이션 응답
│   │   └── ErrorResponse.java       # 에러 응답
│   ├── exception/
│   │   ├── ShelfyException.java     # 기본 커스텀 예외
│   │   ├── ErrorCode.java           # 에러 코드 Enum
│   │   └── GlobalExceptionHandler.java  # @ControllerAdvice
│   ├── util/
│   │   └── DateUtils.java
│   └── constant/
│       └── ShelfyConstants.java
│
├── config/                          # 설정 클래스
│   ├── SecurityConfig.java          # Spring Security 설정
│   ├── JwtConfig.java               # JWT 설정값
│   ├── CorsConfig.java              # CORS 설정
│   ├── MyBatisConfig.java           # MyBatis 설정
│   └── StorageConfig.java           # Object Storage 설정
│
├── auth/                            # 인증/인가 도메인
│   ├── controller/
│   │   └── AuthController.java
│   ├── service/
│   │   ├── AuthService.java
│   │   └── TokenService.java
│   ├── repository/
│   │   ├── RefreshTokenRepository.java
│   │   └── EmailVerificationRepository.java
│   ├── dto/
│   │   ├── request/
│   │   │   ├── SignupRequest.java
│   │   │   ├── LoginRequest.java
│   │   │   └── ResetPasswordRequest.java
│   │   └── response/
│   │       ├── LoginResponse.java
│   │       └── TokenResponse.java
│   └── mapper/                      # MyBatis Mapper (XML)
│       ├── RefreshTokenMapper.java
│       └── EmailVerificationMapper.java
│
├── security/                        # Spring Security 컴포넌트
│   ├── JwtTokenProvider.java        # JWT 생성/검증
│   ├── JwtAuthenticationFilter.java # JWT 필터
│   ├── CustomUserDetails.java       # UserDetails 구현
│   └── CustomUserDetailsService.java
│
├── user/                            # 사용자 도메인
│   ├── controller/
│   │   └── UserController.java
│   ├── service/
│   │   └── UserService.java
│   ├── repository/
│   │   └── UserRepository.java      # JPA Repository
│   ├── entity/
│   │   └── User.java                # JPA Entity
│   ├── dto/
│   │   ├── request/
│   │   │   └── UpdateProfileRequest.java
│   │   └── response/
│   │       ├── UserProfileResponse.java
│   │       └── RevenueResponse.java
│   └── mapper/
│       └── UserMapper.java          # MyBatis (복잡한 조회)
│
├── item/                            # 상품 도메인
│   ├── controller/
│   │   └── ItemController.java
│   ├── service/
│   │   └── ItemService.java
│   ├── repository/
│   │   └── ItemRepository.java      # JPA Repository
│   ├── entity/
│   │   ├── Item.java
│   │   ├── ItemImage.java
│   │   └── SubscriptionPlan.java
│   ├── dto/
│   │   ├── request/
│   │   │   ├── CreateItemRequest.java
│   │   │   ├── UpdateItemRequest.java
│   │   │   └── UpdateItemStatusRequest.java
│   │   └── response/
│   │       ├── ItemDetailResponse.java
│   │       └── ItemSummaryResponse.java
│   └── mapper/
│       └── ItemMapper.java          # MyBatis (검색, 복잡한 목록 조회)
│
├── order/                           # 주문 도메인
│   ├── controller/
│   │   └── OrderController.java
│   ├── service/
│   │   └── OrderService.java
│   ├── repository/
│   │   └── OrderRepository.java
│   ├── entity/
│   │   └── Order.java
│   └── dto/
│       ├── request/
│       │   ├── CreateOrderRequest.java
│       │   └── CancelOrderRequest.java
│       └── response/
│           ├── OrderResponse.java
│           └── OrderDetailResponse.java
│
├── subscription/                    # 구독 도메인
│   ├── controller/
│   │   └── SubscriptionController.java
│   ├── service/
│   │   └── SubscriptionService.java
│   ├── repository/
│   │   ├── SubscriptionRepository.java
│   │   └── SubscriptionPaymentRepository.java
│   ├── entity/
│   │   ├── Subscription.java
│   │   └── SubscriptionPayment.java
│   └── dto/
│       ├── request/
│       │   └── CreateSubscriptionRequest.java
│       └── response/
│           └── SubscriptionResponse.java
│
├── file/                            # 파일 업로드 도메인
│   ├── controller/
│   │   └── FileController.java
│   ├── service/
│   │   ├── FileService.java
│   │   └── StorageService.java      # Object Storage 추상화
│   ├── repository/
│   │   └── FileRepository.java
│   ├── entity/
│   │   └── FileEntity.java
│   └── dto/
│       └── response/
│           └── FileUploadResponse.java
│
└── batch/                           # Spring Batch (2차 확장)
    └── (정기 결제, 토큰 정리 배치)
```

### 2.3 레이어 간 의존성 규칙

```
Controller --> Service --> Repository/Mapper --> DB
     |              |
     v              v
   Request DTO    Entity / Domain Object
   Response DTO
```

- Controller는 Service만 호출한다. Repository를 직접 호출하지 않는다.
- Service는 여러 Repository/Mapper를 조합할 수 있다.
- Entity는 도메인 로직을 포함할 수 있으나 HTTP 관련 코드를 포함하지 않는다.
- DTO는 레이어 간 데이터 전달 전용이며 Entity를 그대로 노출하지 않는다.

### 2.4 JPA vs MyBatis 사용 기준

| 상황 | 사용 기술 | 이유 |
|---|---|---|
| 단순 CRUD (단일 엔티티) | JPA (Spring Data JPA) | 코드 최소화, 영속성 관리 |
| 복잡한 JOIN 조회 (3테이블 이상) | MyBatis | SQL 직접 제어, 성능 예측 가능 |
| 전문 검색 (tsvector) | MyBatis | PostgreSQL 전용 SQL 필요 |
| 집계 쿼리 (수익 현황 등) | MyBatis | 복잡한 GROUP BY/WINDOW FUNCTION |
| 소프트 삭제 필터 포함 목록 조회 | MyBatis | 동적 조건 처리 용이 |

---

## 3. Frontend 디렉토리 구조

### 3.1 Next.js 14 App Router 기반 구조

```
src/
├── app/                             # App Router 루트
│   ├── layout.tsx                   # 루트 레이아웃 (전역 Provider, 폰트)
│   ├── page.tsx                     # 홈 피드 (/)
│   ├── not-found.tsx                # 404 페이지
│   ├── error.tsx                    # 에러 바운더리
│   │
│   ├── (auth)/                      # 인증 관련 Route Group (레이아웃 분리)
│   │   ├── login/
│   │   │   └── page.tsx             # 로그인 페이지
│   │   ├── signup/
│   │   │   └── page.tsx             # 회원가입 페이지
│   │   ├── forgot-password/
│   │   │   └── page.tsx             # 비밀번호 재설정 요청
│   │   └── reset-password/
│   │       └── page.tsx             # 비밀번호 재설정
│   │
│   ├── (main)/                      # 메인 레이아웃 Route Group
│   │   ├── layout.tsx               # Header/Footer 포함 레이아웃
│   │   ├── explore/
│   │   │   └── page.tsx             # 탐색/피드 페이지
│   │   ├── search/
│   │   │   └── page.tsx             # 검색 결과 페이지
│   │   ├── items/
│   │   │   └── [itemId]/
│   │   │       └── page.tsx         # 상품 상세 페이지 (SSR)
│   │   └── users/
│   │       └── [nickname]/
│   │           └── page.tsx         # 셀러 프로필/선반 페이지 (SSR)
│   │
│   └── (dashboard)/                 # 로그인 사용자 대시보드 Route Group
│       ├── layout.tsx               # 사이드바 포함 레이아웃
│       ├── my/
│       │   ├── items/
│       │   │   ├── page.tsx         # 내 상품 목록
│       │   │   ├── new/
│       │   │   │   └── page.tsx     # 상품 등록
│       │   │   └── [itemId]/
│       │   │       └── edit/
│       │   │           └── page.tsx # 상품 수정
│       │   ├── orders/
│       │   │   └── page.tsx         # 구매 내역
│       │   ├── subscriptions/
│       │   │   └── page.tsx         # 구독 내역
│       │   ├── revenue/
│       │   │   └── page.tsx         # 수익 현황
│       │   └── profile/
│       │       └── page.tsx         # 프로필 수정
│       └── verify-email/
│           └── page.tsx             # 이메일 인증 처리
│
├── components/                      # 재사용 컴포넌트
│   ├── ui/                          # 기본 UI 요소 (shadcn/ui 기반)
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   ├── Badge.tsx
│   │   └── ...
│   ├── layout/                      # 레이아웃 컴포넌트
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── Sidebar.tsx
│   │   └── PageContainer.tsx
│   ├── item/                        # 상품 관련 컴포넌트
│   │   ├── ItemCard.tsx             # 상품 카드 (피드용)
│   │   ├── ItemGrid.tsx             # 상품 그리드
│   │   ├── ItemForm.tsx             # 상품 등록/수정 폼
│   │   └── ImageUploader.tsx        # 이미지 업로드
│   ├── auth/                        # 인증 관련 컴포넌트
│   │   ├── LoginForm.tsx
│   │   └── SignupForm.tsx
│   └── common/                      # 공통 컴포넌트
│       ├── Pagination.tsx
│       ├── LoadingSpinner.tsx
│       ├── EmptyState.tsx
│       └── ErrorBoundary.tsx
│
├── lib/                             # 유틸리티 / 설정
│   ├── api/
│   │   ├── client.ts                # Axios 인스턴스 (인터셉터 포함)
│   │   ├── auth.ts                  # 인증 API 함수
│   │   ├── items.ts                 # 상품 API 함수
│   │   ├── orders.ts                # 주문 API 함수
│   │   ├── subscriptions.ts         # 구독 API 함수
│   │   └── users.ts                 # 사용자 API 함수
│   ├── auth/
│   │   ├── tokenManager.ts          # Access Token 메모리 관리
│   │   └── authGuard.ts             # 인증 가드 유틸
│   └── utils/
│       ├── formatters.ts            # 날짜, 금액 포맷
│       └── validators.ts            # 클라이언트 유효성 검사
│
├── hooks/                           # 커스텀 훅
│   ├── useAuth.ts                   # 인증 상태 훅
│   ├── useItems.ts                  # 상품 관련 TanStack Query 훅
│   ├── useOrders.ts
│   ├── useSubscriptions.ts
│   └── useInfiniteScroll.ts
│
├── stores/                          # 클라이언트 상태 관리 (Zustand)
│   ├── authStore.ts                 # 인증 상태 (accessToken 메모리 저장)
│   └── uiStore.ts                  # UI 상태 (모달, 토스트 등)
│
├── types/                           # TypeScript 타입 정의
│   ├── api.ts                       # API 공통 타입 (ApiResponse, PageResponse)
│   ├── auth.ts
│   ├── item.ts
│   ├── order.ts
│   ├── subscription.ts
│   └── user.ts
│
└── styles/
    └── globals.css                  # Tailwind CSS 전역 스타일
```

### 3.2 렌더링 전략 결정 기준

| 페이지 | 렌더링 방식 | 이유 |
|---|---|---|
| 홈 피드 (`/`) | ISR (revalidate: 60초) | SEO 필요, 데이터 변경 빈도 낮음 |
| 상품 상세 (`/items/[id]`) | SSR | SEO 필요, 실시간 정보 필요 |
| 셀러 프로필 (`/users/[nickname]`) | SSR | SEO 필요 |
| 탐색/검색 (`/explore`, `/search`) | CSR | 필터 인터랙션 많음 |
| 대시보드 (`/my/*`) | CSR | 인증 필요, SEO 불필요 |
| 로그인/회원가입 | CSR | SEO 불필요, 인터랙션 중심 |

---

## 4. 인증 구조

### 4.1 전체 인증 흐름

```
[로그인 요청]
    |
    v
POST /auth/login
    |
    |-- 1. 이메일/비밀번호 검증
    |-- 2. 로그인 실패 횟수 확인 (5회 초과 시 잠금)
    |-- 3. Access Token 생성 (JWT, 1시간)
    |-- 4. Refresh Token 생성 (UUID → SHA256 해시 후 DB 저장)
    |
    v
응답:
  - Body: { accessToken, tokenType, expiresIn }
  - Set-Cookie: refreshToken=<raw_token>; HttpOnly; Secure; SameSite=Strict;
                Max-Age=1209600; Path=/auth/token

[클라이언트 상태]
  - Access Token: Zustand 메모리 저장 (window 객체 X, localStorage X)
  - Refresh Token: HttpOnly 쿠키 (JS 접근 불가)
```

### 4.2 Access Token 갱신 흐름

```
[API 요청] --> [Axios 인터셉터]
                    |
                    | Access Token 만료 (401)
                    v
            POST /auth/token/refresh
            (refreshToken 쿠키 자동 포함)
                    |
                    | 성공 시
                    v
            새 Access Token 발급
                    |
                    v
            메모리(Zustand) 업데이트
                    |
                    v
            원래 요청 재시도
```

### 4.3 JWT 구조

**Access Token Payload**

```json
{
  "sub": "1001",
  "email": "user@example.com",
  "nickname": "shelfy_user",
  "emailVerified": true,
  "iat": 1746777600,
  "exp": 1746781200
}
```

**설정값**

| 항목 | 값 |
|---|---|
| 알고리즘 | HS256 |
| Access Token 유효기간 | 1시간 (3600초) |
| Refresh Token 유효기간 | 14일 (1209600초) |
| 시크릿 키 | 환경변수 `JWT_SECRET` (256비트 이상) |

### 4.4 Spring Security 필터 체인

```
HTTP 요청
    |
    v
JwtAuthenticationFilter (OncePerRequestFilter)
    |-- Authorization 헤더에서 Bearer 토큰 추출
    |-- JwtTokenProvider.validateToken()
    |-- SecurityContextHolder에 Authentication 등록
    |
    v
Spring Security Authorization
    |-- Public Endpoint: 인증 불필요
    |-- Protected Endpoint: AUTHENTICATED 필요
    |-- Owner-only: @PreAuthorize("...") 또는 Service 레이어에서 소유권 검증
    |
    v
Controller
```

**Public Endpoint 목록**

```java
// SecurityConfig.java
.requestMatchers(HttpMethod.GET,
    "/api/v1/items",
    "/api/v1/items/{itemId}",
    "/api/v1/items/search",
    "/api/v1/users/{nickname}/profile"
).permitAll()
.requestMatchers(
    "/api/v1/auth/signup",
    "/api/v1/auth/login",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/resend-verification",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/token/refresh"
).permitAll()
```

### 4.5 보안 고려사항

| 위협 | 대응 방안 |
|---|---|
| XSS를 통한 토큰 탈취 | Access Token 메모리 저장, Refresh Token HttpOnly 쿠키 |
| CSRF | SameSite=Strict 쿠키, Origin 검증 |
| Refresh Token 탈취 | DB 저장으로 강제 무효화 가능, token_hash만 DB에 저장 |
| 무차별 대입 | 5회 실패 시 30분 계정 잠금 |
| JWT 알고리즘 혼동 | alg 헤더 검증, none 알고리즘 차단 |

---

## 5. 이미지 업로드 처리 방식

### 5.1 업로드 흐름

```
[클라이언트]
    |
    | 1. POST /api/v1/files/upload (multipart/form-data)
    |    - file: 이미지 파일
    |    - type: ITEM_IMAGE | PROFILE_IMAGE
    v
[Backend - FileController]
    |
    | 2. 파일 유효성 검사
    |    - 확장자: JPG, PNG, WEBP만 허용
    |    - MIME 타입 검증 (확장자 스푸핑 방지)
    |    - 크기: 최대 10MB
    v
[StorageService]
    |
    | 3. UUID 기반 파일명 생성 (stored_name)
    | 4. Object Storage(MinIO/Cloud)에 업로드
    | 5. CDN URL 생성
    v
[DB - files 테이블]
    | 6. 파일 메타데이터 저장
    |    - uploader_id, file_type, original_name, stored_name, cdn_url, file_size, mime_type
    v
[응답]
    | 7. imageId, url 반환
    v
[클라이언트]
    | 8. 반환된 imageId를 상품 등록/수정 요청에 포함
    v
[POST /api/v1/items - 상품 등록]
    | 9. imageIds로 item_images 연결
```

### 5.2 저장소 구성

| 환경 | Object Storage | CDN |
|---|---|---|
| 로컬 개발 | MinIO (Docker) | MinIO 직접 URL |
| 운영 | Cloud Object Storage | CDN 배포 (별도 도메인) |

### 5.3 파일 보안

- Content-Type 헤더 검증 + Magic Bytes 검증 (Apache Tika 활용)
- 파일명은 UUID로 생성하여 원본명 노출 방지
- 업로드 파일은 서버 로컬 저장 없이 스트림으로 Object Storage 전송
- 미사용 파일 정리: 업로드 후 24시간 내 상품/프로필에 미연결 시 배치로 삭제 (2차)

---

## 6. Docker Compose 구성 개요

### 6.1 서비스 목록

| 서비스명 | 이미지 | 포트 | 역할 |
|---|---|---|---|
| postgres | postgres:15-alpine | 5432 | 데이터베이스 |
| backend | shelfy/backend:latest | 8080 | Spring Boot API 서버 |
| frontend | shelfy/frontend:latest | 3000 | Next.js 앱 서버 |
| minio | minio/minio:latest | 9000, 9001 | Object Storage (개발용) |

### 6.2 환경변수 관리

```
Shelfy/
├── .env.example          # 환경변수 템플릿 (Git 추적)
├── .env                  # 실제 환경변수 (Git 제외)
├── backend/
│   └── .env.local        # Backend 전용 환경변수 (Git 제외)
└── frontend/
    └── .env.local        # Frontend 전용 환경변수 (Git 제외)
```

**필수 환경변수 목록**

```
# DB
POSTGRES_DB=shelfy
POSTGRES_USER=shelfy_user
POSTGRES_PASSWORD=<secret>

# JWT
JWT_SECRET=<256비트 이상 랜덤 문자열>

# MinIO (개발)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<secret>
MINIO_BUCKET=shelfy-images

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8080/api/v1
```

### 6.3 볼륨 전략

| 볼륨명 | 마운트 경로 | 용도 |
|---|---|---|
| postgres_data | /var/lib/postgresql/data | DB 데이터 영속화 |
| minio_data | /data | 이미지 파일 영속화 |

---

## 7. 기술 결정 사항 (ADR)

### ADR-001: JPA + MyBatis 혼용

- **결정**: 단순 CRUD는 JPA, 복잡한 조회/집계는 MyBatis 사용
- **근거**: JPA는 개발 생산성, MyBatis는 복잡한 SQL 제어 가능. PostgreSQL 전용 기능(tsvector, Array) 활용 시 MyBatis 필수
- **적용 범위**: 검색, 목록 조회 (필터+정렬), 수익 집계 쿼리는 MyBatis

### ADR-002: Refresh Token DB 저장

- **결정**: Refresh Token을 DB에 해시값으로 저장
- **근거**: 강제 로그아웃, 다중 기기 토큰 무효화, 탈취 시 즉시 차단 가능
- **트레이드오프**: 토큰 검증마다 DB 조회 발생 → 만료/revoke 여부만 조회, 인덱스 적용으로 성능 수용

### ADR-003: Next.js App Router 채택

- **결정**: Page Router 대신 App Router 사용
- **근거**: Server Component로 초기 데이터 fetch 최적화, SEO 대응, Next.js 14 권장 방식
- **주의**: 인증이 필요한 Client Component에서 useAuth 훅으로 accessToken 메모리 접근

### ADR-004: PostgreSQL Array 타입으로 태그 관리

- **결정**: 별도 tags 테이블 없이 `VARCHAR(20)[]` 배열 컬럼 사용
- **근거**: 태그는 상품에만 종속, 별도 정규화 불필요, GIN 인덱스로 검색 가능
- **한계**: 태그 통계/인기 태그 집계 시 쿼리 복잡도 증가 → 2차에서 별도 테이블 검토

### ADR-005: 이미지 업로드 선업로드(Pre-upload) 방식

- **결정**: 상품 등록 전 이미지를 먼저 업로드하고 반환된 imageId 사용
- **근거**: 상품 등록 폼에서 미리보기 기능 지원, 상품 등록 실패 시 이미지 재업로드 불필요
- **주의**: 미연결 파일 정리 배치 필요 (2차 구현)
