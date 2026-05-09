# 기술 아키텍처 문서

- **프로젝트명**: 발자국 (Foot-Print)
- **문서 버전**: v1.0.0
- **작성일**: 2026-05-09
- **작성자**: DevLead
- **상태**: 확정

---

## 목차

1. [전체 시스템 구성도](#1-전체-시스템-구성도)
2. [레이어 역할 및 책임](#2-레이어-역할-및-책임)
3. [지도 API 선택 결정](#3-지도-api-선택-결정)
4. [파일 업로드 전략](#4-파일-업로드-전략)
5. [JWT 토큰 전략](#5-jwt-토큰-전략)
6. [데이터베이스 구조 개요](#6-데이터베이스-구조-개요)
7. [배포 구성](#7-배포-구성)

---

## 1. 전체 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────────┐
│                          사용자 브라우저                               │
│                   Next.js 14 (App Router / SSR)                       │
│                   React 18 / TypeScript / TailwindCSS                 │
│                   Zustand (전역 상태) / TanStack Query (서버 상태)      │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS (REST API / JSON)
                             │ Authorization: Bearer {accessToken}
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Backend API Server                               │
│                   Spring Boot 3.x (Java 17)                           │
│                   Spring Security + JWT                               │
│                   Spring Data JPA / Hibernate                         │
│                   포트: 8080                                           │
└──────┬─────────────────────┬───────────────────────────────────────┘
       │                     │
       ▼                     ▼
┌─────────────┐    ┌──────────────────────────────────────────────────┐
│ PostgreSQL  │    │            외부 API                               │
│    16       │    │  Kakao Maps API (지도, 지오코딩, 장소 검색)          │
│ 포트: 5432  │    │  - JavaScript SDK (프론트엔드에서 직접 호출)         │
│             │    │  - REST API (백엔드에서 필요 시 호출)               │
└─────────────┘    └──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   로컬 파일 스토리지 (Docker Volume)                   │
│         /app/uploads/places/{userId}/{placeId}/                       │
│         /app/uploads/profiles/{userId}/                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.1 네트워크 흐름 상세

```
[브라우저]
  ├── 정적 자원 (HTML/CSS/JS): Next.js 서버 (포트 3000)
  ├── 지도 렌더링: Kakao Maps JavaScript SDK (CDN)
  └── API 호출: Spring Boot 서버 (포트 8080)
        ├── 인증 확인: Spring Security Filter
        ├── 비즈니스 로직: Service Layer
        ├── 데이터 조회/저장: PostgreSQL (포트 5432)
        └── 파일 I/O: 로컬 볼륨
```

### 1.2 Docker Compose 컨테이너 구성

| 컨테이너 | 이미지 | 내부 포트 | 외부 포트 | 역할 |
|----------|--------|----------|----------|------|
| `footprint-db` | postgres:16-alpine | 5432 | 5432 | 데이터 저장 |
| `footprint-backend` | openjdk:17-jdk-slim | 8080 | 8080 | API 서버 |
| `footprint-frontend` | node:20-alpine | 3000 | 3000 | Next.js 서버 |

---

## 2. 레이어 역할 및 책임

### 2.1 Frontend 레이어

| 계층 | 기술 | 책임 |
|------|------|------|
| Presentation | React 18 컴포넌트, TailwindCSS | UI 렌더링, 사용자 인터랙션 처리 |
| Routing | Next.js 14 App Router | 페이지 라우팅, 레이아웃 구성, 미들웨어 인증 |
| Server State | TanStack Query (React Query) | API 데이터 캐싱, 동기화, 로딩/에러 상태 관리 |
| Client State | Zustand | 로그인 사용자 정보, 지도 필터 상태, UI 전역 상태 |
| API 통신 | Axios (인터셉터) | 공통 헤더, 토큰 자동 갱신, 에러 핸들링 |
| 타입 안전성 | TypeScript | 컴파일 타임 타입 검증 |

**Next.js 렌더링 전략 기준**:
- 로그인/회원가입 페이지: CSR (Client-Side Rendering) - 인터랙션 중심
- 장소 목록/상세 페이지: CSR (사용자별 개인 데이터이므로 SSR 불필요)
- 지도 페이지: CSR (Kakao Maps SDK는 브라우저 환경에서만 동작)
- 통계 페이지: CSR
- 공통 레이아웃: Server Component (GNB 정적 구조)

### 2.2 Backend 레이어

```
┌──────────────────────────────────────────────────────┐
│  Presentation Layer (Controller)                      │
│  - REST API 엔드포인트 정의                            │
│  - 요청 파라미터 유효성 검사 (@Valid)                  │
│  - 공통 응답 포맷 (ApiResponse<T>) 변환                │
├──────────────────────────────────────────────────────┤
│  Business Layer (Service)                             │
│  - 핵심 비즈니스 로직 구현                             │
│  - 트랜잭션 경계 관리 (@Transactional)                 │
│  - 도메인 객체 조작                                    │
├──────────────────────────────────────────────────────┤
│  Persistence Layer (Repository)                       │
│  - Spring Data JPA Repository                         │
│  - 복잡한 동적 쿼리: QueryDSL 또는 JPQL               │
│  - 엔티티 ↔ DB 매핑                                   │
├──────────────────────────────────────────────────────┤
│  Cross-Cutting Concerns                               │
│  - Spring Security (인증/인가 필터)                    │
│  - GlobalExceptionHandler (전역 예외 처리)             │
│  - AOP 로깅 (API 요청/응답 로깅)                       │
└──────────────────────────────────────────────────────┘
```

**패키지 구조 원칙**: 도메인 중심 패키지 (domain-driven packaging)
- `com.footprint.{domain}.controller` - 컨트롤러
- `com.footprint.{domain}.service` - 서비스
- `com.footprint.{domain}.repository` - 레포지토리
- `com.footprint.{domain}.dto` - 데이터 전송 객체
- `com.footprint.{domain}.entity` - JPA 엔티티

### 2.3 Database 레이어

| 요소 | 결정 사항 |
|------|----------|
| DBMS | PostgreSQL 16 |
| ORM | Spring Data JPA / Hibernate |
| 연결 풀 | HikariCP (Spring Boot 기본) |
| 소프트 딜리트 | `deleted_at TIMESTAMP NULL` 컬럼으로 관리 |
| 좌표 저장 | `DECIMAL(10, 8)` / `DECIMAL(11, 8)` (위도/경도) |
| UUID 전략 | User 테이블 PK는 UUID, 나머지는 BIGINT AUTO_INCREMENT |

---

## 3. 지도 API 선택 결정

### 3.1 결정 사항

**선택: Kakao Maps API (JavaScript SDK v3 + REST API)**

### 3.2 선택 근거

| 평가 항목 | Kakao Maps API | Google Maps API | 결정 근거 |
|----------|---------------|----------------|----------|
| 국내 지명 정확도 | 최상 | 양호 | 국내 서비스이므로 Kakao 우위 |
| 무료 사용량 | 월 300,000 트랜잭션 무료 | 월 $200 크레딧 (약 28,000 Dynamic Map 로드) | Kakao가 초기 서비스에 경제적 |
| 클러스터링 지원 | 공식 MarkerClusterer 라이브러리 제공 | 별도 라이브러리 필요 | Kakao 개발 편의성 우위 |
| 한국어 주소 검색 | 카카오 로컬 REST API 연동 자연스러움 | 지오코딩 API 별도 | Kakao 일관성 우위 |
| 개발 문서 | 한국어 공식 문서 제공 | 영어 공식 문서 | 팀 협업 효율 측면 Kakao 우위 |

### 3.3 Kakao Maps API 적용 방식

**프론트엔드 (JavaScript SDK)**:
- 지도 렌더링, 마커 표시, 클러스터링, 지도 클릭 이벤트
- Next.js `Script` 컴포넌트로 SDK 비동기 로딩
- `window.kakao.maps` 객체는 CSR 환경에서만 접근 (dynamic import 활용)

**백엔드 (Kakao Local REST API)**:
- 필요 시 서버 측에서 주소 → 좌표 변환 (Geocoding)
- 단, 일반적인 경우 프론트엔드 SDK에서 직접 처리하여 백엔드 부하 최소화

**환경변수 관리**:
```
# 프론트엔드
NEXT_PUBLIC_KAKAO_MAP_APP_KEY=발급받은_JavaScript_키

# 백엔드 (필요 시)
KAKAO_REST_API_KEY=발급받은_REST_API_키
```

---

## 4. 파일 업로드 전략

### 4.1 결정 사항

**로컬 스토리지 기반 Multipart 업로드** (초기 버전)

초기 서비스 규모를 고려하여 S3와 같은 외부 스토리지 대신 Docker Volume 기반 로컬 스토리지를 사용한다.
서비스 성장 시 스토리지 추상화 레이어(StorageService 인터페이스)를 통해 S3로 전환 가능한 구조로 설계한다.

### 4.2 파일 저장 구조

```
/app/uploads/
├── places/
│   └── {userId}/
│       └── {placeId}/
│           ├── {uuid}_original.jpg      # 원본 파일
│           └── {uuid}_thumb.jpg         # 썸네일 (300x300 리사이즈)
└── profiles/
    └── {userId}/
        ├── {uuid}_original.jpg
        └── {uuid}_thumb.jpg
```

### 4.3 파일 업로드 처리 흐름

```
클라이언트
  │
  ├── [1] Multipart/form-data로 POST 요청
  │
Backend (Spring Boot)
  ├── [2] MultipartFile 수신
  ├── [3] 파일 유효성 검사
  │       - 확장자 화이트리스트: jpg, jpeg, png, webp
  │       - MIME 타입 검증 (Magic Bytes 확인)
  │       - 파일 크기 확인 (장소 사진: 10MB, 프로필: 2MB)
  │       - 장소 사진 개수 확인 (최대 5장)
  ├── [4] UUID 기반 파일명 재생성 (보안)
  ├── [5] 썸네일 생성 (300x300, Java Image I/O)
  ├── [6] 로컬 볼륨에 원본 + 썸네일 저장
  ├── [7] DB에 파일 경로 및 메타데이터 저장
  └── [8] 클라이언트에 접근 URL 반환
```

### 4.4 파일 접근 URL

정적 파일 서빙은 Spring Boot의 `ResourceHttpRequestHandler`를 활용한다.

```
GET /api/v1/files/{filePath}  →  /app/uploads/{filePath} 반환
```

접근 URL 예시:
```
https://api.footprint.example.com/api/v1/files/places/uuid-user/uuid-place/uuid-file_thumb.jpg
```

### 4.5 StorageService 인터페이스 (확장성 고려)

```java
public interface StorageService {
    String store(MultipartFile file, String directory);
    void delete(String filePath);
    String getFileUrl(String filePath);
}

// 현재 구현체
@Service
@Profile("!prod")
public class LocalStorageService implements StorageService { ... }

// 향후 확장 구현체 (미구현)
// @Service
// @Profile("prod")
// public class S3StorageService implements StorageService { ... }
```

---

## 5. JWT 토큰 전략

### 5.1 토큰 구성

| 구분 | Access Token | Refresh Token |
|------|-------------|--------------|
| 유효 기간 | 30분 | 7일 |
| 저장 위치 | 메모리 (Zustand store) | HttpOnly Cookie |
| 전송 방식 | `Authorization: Bearer {token}` 헤더 | 쿠키 자동 전송 |
| 갱신 트리거 | 401 TOKEN_EXPIRED 응답 수신 시 | 로그인 시 신규 발급 |

**Access Token을 메모리 저장으로 결정한 이유**:
- LocalStorage/SessionStorage 저장 시 XSS 공격에 취약
- HttpOnly Cookie 저장 시 CSRF 취약점 고려 필요 (SameSite=Strict로 완화 가능하나 복잡도 증가)
- 메모리 저장은 탭 새로고침 시 토큰이 사라지지만, Refresh Token으로 자동 재발급하여 UX 유지

### 5.2 JWT Payload 구조

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "nickname": "홍길동",
  "type": "ACCESS",
  "iat": 1715000000,
  "exp": 1715001800
}
```

### 5.3 Refresh Token 관리 전략

Refresh Token은 DB에도 저장하여 로그아웃 및 탈퇴 시 즉시 무효화 처리한다.

```
DB 테이블: refresh_tokens
  - id (PK)
  - user_id (FK)
  - token (해시값 저장)
  - expires_at
  - created_at
  - is_revoked (로그아웃/탈퇴 시 true 설정)
```

### 5.4 토큰 갱신 흐름 (Frontend Axios 인터셉터)

```
[API 요청]
    │
    ├── 정상 응답 → 처리 완료
    │
    └── 401 TOKEN_EXPIRED
            │
            ├── POST /api/v1/auth/refresh (Refresh Token 쿠키 자동 포함)
            │
            ├── 신규 Access Token 수신 → 메모리 저장
            │
            ├── 원래 요청 재시도 (신규 토큰 포함)
            │
            └── 401 REFRESH_TOKEN_EXPIRED
                    │
                    └── Zustand 인증 상태 초기화 → /login 이동
```

### 5.5 Cookie 설정

```
Set-Cookie: refresh_token={token}; HttpOnly; Secure; SameSite=Strict; Max-Age=604800; Path=/api/v1/auth
```

| 속성 | 값 | 목적 |
|------|---|------|
| HttpOnly | true | JavaScript 접근 차단 (XSS 방지) |
| Secure | true | HTTPS 전송만 허용 |
| SameSite | Strict | CSRF 방지 |
| Path | /api/v1/auth | Refresh Token 관련 엔드포인트에만 전송 |

---

## 6. 데이터베이스 구조 개요

### 6.1 핵심 테이블 목록

| 테이블 | 설명 |
|--------|------|
| `users` | 사용자 계정 정보 |
| `refresh_tokens` | Refresh Token 관리 |
| `categories` | 장소 카테고리 (기본 + 사용자 정의) |
| `places` | 장소 기록 |
| `place_categories` | 장소-카테고리 다대다 연결 |
| `place_tags` | 장소 태그 |
| `place_photos` | 장소 사진 |

### 6.2 주요 설계 결정

- **소프트 딜리트**: `places`, `users` 테이블에 `deleted_at TIMESTAMP NULL` 적용
- **감사 컬럼**: 모든 테이블에 `created_at`, `updated_at` 적용 (JPA Auditing)
- **인덱스 전략**: DBA와 협의하여 `places.user_id`, `places.visited_at`, `places.deleted_at` 조합 인덱스 설계 예정
- **카테고리 기본값**: `categories.is_default = true` 레코드는 애플리케이션 시작 시 DataInitializer로 삽입

---

## 7. 배포 구성

### 7.1 개발 환경

```
로컬 개발: Docker Compose (docker-compose.yml)
  - footprint-db (PostgreSQL 16)
  - footprint-backend (Spring Boot, 빌드 후 실행)
  - footprint-frontend (Next.js)
```

### 7.2 환경 분리

| 환경 | 프로파일 | 설정 파일 |
|------|---------|----------|
| 로컬 개발 | local | application-local.yml |
| 운영 | prod | 환경변수로 주입 |

### 7.3 헬스체크

```
GET /api/v1/health → { "status": "UP", "timestamp": "..." }
```

Docker Compose `healthcheck` 설정으로 백엔드 컨테이너 준비 상태 확인 후 프론트엔드 컨테이너 시작.

### 7.4 CI/CD (향후 계획)

```
GitHub Actions Workflow:
  push to develop → 빌드 + 테스트
  push to main → 빌드 + 테스트 + Docker 이미지 빌드 + 배포
```

---

*문서 끝 - 변경 사항 발생 시 BackendSenior, FrontendSenior, DBA에게 즉시 공유한다.*
