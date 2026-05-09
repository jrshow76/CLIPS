# 개발 컨벤션 문서

- **프로젝트명**: 발자국 (Foot-Print)
- **문서 버전**: v1.0.0
- **작성일**: 2026-05-09
- **작성자**: DevLead
- **상태**: 확정

---

## 목차

1. [Backend 컨벤션](#1-backend-컨벤션)
2. [Frontend 컨벤션](#2-frontend-컨벤션)
3. [Git 브랜치 전략](#3-git-브랜치-전략)
4. [PR 규칙 및 커밋 메시지 컨벤션](#4-pr-규칙-및-커밋-메시지-컨벤션)

---

## 1. Backend 컨벤션

### 1.1 패키지 구조

도메인 중심 패키지 구조를 사용한다. 기술 레이어(controller, service 등)를 도메인 하위에 배치한다.

```
com.footprint/
├── FootprintApplication.java           # 애플리케이션 진입점
├── common/                             # 공통 모듈 (도메인 비의존)
│   ├── response/
│   │   └── ApiResponse.java            # 공통 응답 DTO
│   ├── exception/
│   │   ├── GlobalExceptionHandler.java # 전역 예외 핸들러
│   │   ├── CustomException.java        # 비즈니스 예외 기반 클래스
│   │   └── ErrorCode.java              # 에러 코드 enum
│   └── security/
│       ├── JwtTokenProvider.java       # JWT 생성/검증
│       ├── JwtAuthenticationFilter.java
│       └── SecurityConfig.java
├── auth/
│   ├── controller/AuthController.java
│   ├── service/AuthService.java
│   ├── dto/
│   │   ├── LoginRequest.java
│   │   ├── SignupRequest.java
│   │   └── TokenResponse.java
│   └── entity/
│       ├── User.java
│       └── RefreshToken.java
├── place/
│   ├── controller/PlaceController.java
│   ├── service/PlaceService.java
│   ├── repository/PlaceRepository.java
│   ├── dto/
│   │   ├── PlaceRequest.java
│   │   ├── PlaceResponse.java
│   │   └── PlaceSummaryResponse.java
│   └── entity/
│       ├── Place.java
│       ├── PlaceCategory.java
│       ├── PlaceTag.java
│       └── PlacePhoto.java
├── category/
│   ├── controller/CategoryController.java
│   ├── service/CategoryService.java
│   ├── repository/CategoryRepository.java
│   └── entity/Category.java
└── stats/
    └── controller/StatsController.java
```

### 1.2 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 클래스 | PascalCase | `PlaceService`, `ApiResponse` |
| 메서드 | camelCase, 동사로 시작 | `getPlaceById`, `createPlace`, `deletePlace` |
| 변수/파라미터 | camelCase | `placeId`, `userId`, `visitedAt` |
| 상수 | UPPER_SNAKE_CASE | `MAX_PHOTO_COUNT`, `DEFAULT_PAGE_SIZE` |
| 패키지 | 소문자 | `com.footprint.place.service` |
| DB 컬럼/테이블 | snake_case | `place_id`, `visited_at`, `is_default` |
| API URL | 소문자 + 하이픈 | `/api/v1/places`, `/place-photos` |
| Enum 값 | UPPER_SNAKE_CASE | `PLACE_NOT_FOUND`, `AUTH_FAILED` |

**메서드 네이밍 접두사 기준**:

| 접두사 | 용도 |
|--------|------|
| `get` | 단건 조회 (없으면 예외 발생) |
| `find` | 단건 조회 (없으면 Optional/null 반환) |
| `list`, `getAll` | 목록 조회 |
| `create` | 신규 생성 |
| `update` | 수정 |
| `delete` | 삭제 |
| `validate` | 유효성 검사 |
| `is`, `has`, `can` | 불리언 반환 |

### 1.3 공통 응답 포맷 (ApiResponse<T>)

모든 API 응답은 반드시 `ApiResponse<T>`로 감싸서 반환한다.

```java
@Getter
@Builder
public class ApiResponse<T> {
    private final boolean success;
    private final String code;
    private final String message;
    private final T data;
    private final List<FieldError> errors;
    private final String timestamp;

    // 성공 응답
    public static <T> ApiResponse<T> success(T data) { ... }
    public static <T> ApiResponse<T> success(String message, T data) { ... }

    // 실패 응답
    public static <T> ApiResponse<T> fail(ErrorCode errorCode) { ... }
    public static <T> ApiResponse<T> fail(ErrorCode errorCode, List<FieldError> errors) { ... }
}
```

**사용 예시**:

```java
// 성공 (200)
return ResponseEntity.ok(ApiResponse.success("장소가 조회되었습니다.", placeResponse));

// 생성 성공 (201)
return ResponseEntity.status(HttpStatus.CREATED)
    .body(ApiResponse.success("장소가 등록되었습니다.", placeResponse));

// 실패
throw new CustomException(ErrorCode.PLACE_NOT_FOUND);
```

### 1.4 예외 처리 구조

**계층 구조**:

```
Exception
└── RuntimeException
    └── CustomException (com.footprint.common.exception)
        └── ErrorCode enum으로 에러 코드 + HTTP 상태 + 메시지 관리
```

**CustomException 사용 원칙**:
- Service 레이어에서 비즈니스 규칙 위반 시 `throw new CustomException(ErrorCode.XXX)` 사용
- Controller 레이어에서는 예외를 잡지 않고 `GlobalExceptionHandler`에 위임
- Repository 레이어에서는 JPA 예외를 Service에서 처리

**GlobalExceptionHandler 처리 대상**:

| 예외 타입 | HTTP 상태 | 처리 방식 |
|----------|----------|----------|
| `CustomException` | ErrorCode에 정의된 상태 | ErrorCode 기반 응답 |
| `MethodArgumentNotValidException` | 400 | 필드별 유효성 오류 응답 |
| `ConstraintViolationException` | 400 | 유효성 오류 응답 |
| `AccessDeniedException` | 403 | FORBIDDEN 응답 |
| `AuthenticationException` | 401 | UNAUTHORIZED 응답 |
| `MaxUploadSizeExceededException` | 413 | FILE_TOO_LARGE 응답 |
| `Exception` (그 외) | 500 | SERVER_ERROR 응답 (스택 트레이스 로그) |

### 1.5 공통 규칙

- **@Transactional**: Service 클래스 또는 메서드 단위로 선언. 조회 메서드는 `@Transactional(readOnly = true)` 적용
- **DTO 변환**: Service 레이어에서 Entity → DTO 변환 수행. Controller는 DTO만 다룬다
- **Lombok 사용**: `@Getter`, `@Builder`, `@RequiredArgsConstructor` 우선 사용. `@Data` 사용 금지 (equals/hashCode 의도치 않은 동작 방지)
- **로그**: `@Slf4j` 사용, `log.info`, `log.warn`, `log.error` 레벨 구분 준수
- **소프트 딜리트**: `@SQLDelete` + `@Where` 어노테이션으로 JPA 레벨에서 자동 처리

---

## 2. Frontend 컨벤션

### 2.1 디렉토리 구조

```
frontend/src/
├── app/                              # Next.js App Router 페이지
│   ├── layout.tsx                    # 루트 레이아웃
│   ├── page.tsx                      # 루트 페이지 (지도로 redirect)
│   ├── (auth)/                       # 인증 그룹 라우트 (레이아웃 별도)
│   │   ├── login/page.tsx
│   │   └── signup/page.tsx
│   ├── places/
│   │   ├── page.tsx                  # 장소 목록
│   │   ├── [id]/page.tsx             # 장소 상세
│   │   └── new/page.tsx              # 장소 등록
│   ├── map/page.tsx
│   ├── stats/page.tsx
│   └── mypage/page.tsx
├── components/
│   ├── common/                       # 도메인 독립적 공통 컴포넌트
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   ├── Toast.tsx
│   │   └── Loading.tsx
│   ├── place/                        # 장소 도메인 컴포넌트
│   │   ├── PlaceCard.tsx
│   │   ├── PlaceForm.tsx
│   │   └── PlaceList.tsx
│   ├── map/                          # 지도 도메인 컴포넌트
│   │   ├── MapView.tsx
│   │   └── MapMarker.tsx
│   └── layout/                       # 레이아웃 구성 컴포넌트
│       ├── GNB.tsx
│       └── Layout.tsx
├── lib/
│   ├── api/
│   │   ├── axios.ts                  # Axios 인스턴스 + 인터셉터
│   │   ├── auth.api.ts
│   │   ├── place.api.ts
│   │   ├── category.api.ts
│   │   └── stats.api.ts
│   └── hooks/
│       ├── useAuth.ts
│       ├── usePlace.ts
│       └── useCategory.ts
├── store/
│   ├── authStore.ts                  # 인증 상태 (Zustand)
│   └── uiStore.ts                    # UI 전역 상태 (Zustand)
└── types/
    ├── auth.types.ts
    ├── place.types.ts
    ├── category.types.ts
    └── api.types.ts                  # ApiResponse, PageResponse 등 공통 타입
```

### 2.2 컴포넌트 네이밍

| 대상 | 규칙 | 예시 |
|------|------|------|
| 컴포넌트 파일 | PascalCase.tsx | `PlaceCard.tsx`, `Button.tsx` |
| 페이지 파일 | Next.js 규칙 (소문자) | `page.tsx`, `layout.tsx` |
| 훅 파일 | camelCase, `use` 접두사 | `useAuth.ts`, `usePlace.ts` |
| 스토어 파일 | camelCase, `Store` 접미사 | `authStore.ts`, `uiStore.ts` |
| 타입 파일 | camelCase, `.types.ts` 접미사 | `place.types.ts` |
| API 함수 파일 | camelCase, `.api.ts` 접미사 | `place.api.ts` |

**컴포넌트 작성 원칙**:

```typescript
// 컴포넌트 Props 타입은 컴포넌트명 + Props 접미사
interface PlaceCardProps {
  place: PlaceSummary;
  onClick?: (placeId: number) => void;
}

// 함수형 컴포넌트, named export 사용 (default export 금지)
export function PlaceCard({ place, onClick }: PlaceCardProps) {
  // ...
}
```

**default export 금지 이유**: 리팩토링 시 컴포넌트명 불일치 발생 방지, IDE 자동 import 정확성 보장

### 2.3 API 클라이언트 구조

**Axios 인스턴스 (`src/lib/api/axios.ts`)**:

```typescript
// 싱글턴 Axios 인스턴스
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  timeout: 30000,
  withCredentials: true, // Refresh Token 쿠키 자동 전송
});

// Request 인터셉터: Access Token 헤더 자동 추가
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response 인터셉터: 401 시 토큰 갱신 후 재시도
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    // TOKEN_EXPIRED → refresh → 재시도
    // REFRESH_TOKEN_EXPIRED → 로그인 이동
  }
);
```

**API 함수 작성 규칙**:

```typescript
// src/lib/api/place.api.ts
export const placeApi = {
  getPlaces: (params: GetPlacesParams) =>
    apiClient.get<ApiResponse<PageResponse<PlaceSummary>>>('/places', { params }),

  getPlaceById: (placeId: number) =>
    apiClient.get<ApiResponse<PlaceDetail>>(`/places/${placeId}`),

  createPlace: (data: CreatePlaceRequest) =>
    apiClient.post<ApiResponse<PlaceDetail>>('/places', data),

  updatePlace: (placeId: number, data: UpdatePlaceRequest) =>
    apiClient.put<ApiResponse<PlaceDetail>>(`/places/${placeId}`, data),

  deletePlace: (placeId: number) =>
    apiClient.delete<ApiResponse<null>>(`/places/${placeId}`),
};
```

**TanStack Query 훅 작성 규칙**:

```typescript
// src/lib/hooks/usePlace.ts
export function usePlaces(params: GetPlacesParams) {
  return useQuery({
    queryKey: ['places', params],
    queryFn: () => placeApi.getPlaces(params).then((res) => res.data.data),
  });
}

export function useCreatePlace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: placeApi.createPlace,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['places'] });
    },
  });
}
```

### 2.4 상태 관리 기준

| 상태 유형 | 관리 방식 | 예시 |
|----------|----------|------|
| 서버 데이터 | TanStack Query | 장소 목록, 카테고리 목록 |
| 전역 클라이언트 상태 | Zustand | 로그인 사용자 정보, Access Token, 토스트 메시지 |
| 로컬 UI 상태 | useState | 모달 열림 여부, 폼 입력값 |
| URL 기반 상태 | useSearchParams | 검색 키워드, 필터, 페이지 번호 |

### 2.5 공통 규칙

- **TypeScript strict 모드**: `tsconfig.json`의 `"strict": true` 유지. `any` 타입 사용 금지
- **환경변수**: 클라이언트 노출 변수는 `NEXT_PUBLIC_` 접두사 필수
- **에러 바운더리**: 페이지 단위로 `error.tsx` 파일로 에러 UI 처리
- **Loading 상태**: TanStack Query `isPending` 상태를 기반으로 `<Loading />` 컴포넌트 표시
- **이미지**: Next.js `<Image />` 컴포넌트 사용 필수 (성능 최적화)
- **스타일**: TailwindCSS 클래스 우선 사용. 커스텀 CSS는 최소화

---

## 3. Git 브랜치 전략

### 3.1 브랜치 구조

```
main
  └── develop
        ├── feature/{issue-id}-{brief-description}
        ├── feature/{issue-id}-{brief-description}
        └── hotfix/{issue-id}-{brief-description}
```

### 3.2 브랜치 역할

| 브랜치 | 역할 | 병합 대상 | 직접 Push |
|--------|------|----------|----------|
| `main` | 운영 배포 상태 (항상 배포 가능) | `develop` → `main` (PR) | 금지 |
| `develop` | 통합 개발 브랜치 | `feature/*` → `develop` (PR) | 금지 |
| `feature/*` | 기능 개발 | 완료 후 `develop`으로 PR | 작업자만 |
| `hotfix/*` | 운영 긴급 수정 | `main` + `develop` 양쪽으로 PR | 작업자만 |

### 3.3 브랜치 네이밍 규칙

```
feature/{issue-id}-{brief-description}

예시:
  feature/FP-001-auth-login
  feature/FP-015-place-list-api
  feature/FP-023-map-marker-clustering
  hotfix/FP-099-fix-jwt-expiry-error
```

### 3.4 작업 흐름

```
1. GitHub Issue 또는 Jira 티켓 생성
2. develop에서 feature 브랜치 생성
   git checkout develop
   git pull origin develop
   git checkout -b feature/FP-001-auth-login

3. 기능 개발 및 커밋

4. develop으로 PR 생성
   - PR 제목: [FP-001] 로그인 API 구현
   - 리뷰어: DevLead 필수 지정

5. DevLead 코드 리뷰 승인 후 Squash Merge

6. feature 브랜치 삭제
```

---

## 4. PR 규칙 및 커밋 메시지 컨벤션

### 4.1 PR 규칙

**PR 생성 필수 조건**:
- [ ] 로컬 빌드 성공 확인
- [ ] 신규 기능에 대한 기본 테스트 작성
- [ ] PR 템플릿 항목 모두 작성

**PR 제목 형식**:
```
[{이슈ID}] {작업 요약}

예시:
  [FP-001] 로그인/회원가입 API 구현
  [FP-015] 장소 목록 조회 + 검색/필터링 API 구현
  [FP-023] 지도 마커 클러스터링 컴포넌트 구현
```

**PR 본문 템플릿**:

```markdown
## 작업 내용
- [ ] 구현 항목 1
- [ ] 구현 항목 2

## 변경 이유
> 왜 이 변경이 필요한가?

## 관련 이슈
- Closes #{이슈번호}

## 스크린샷 (UI 변경 시 필수)
<!-- Before / After 스크린샷 첨부 -->

## 체크리스트
- [ ] 빌드 성공
- [ ] 관련 테스트 추가/수정
- [ ] API 규약 준수 (ApiResponse<T> 포맷)
- [ ] 네이밍 컨벤션 준수
```

**리뷰 규칙**:
- 리뷰어는 반드시 DevLead를 지정한다
- 최소 1명의 승인 후 병합 가능
- Resolve 되지 않은 리뷰 코멘트가 있으면 병합 금지
- 코드 리뷰는 PR 생성 후 24시간 내 완료를 목표로 한다

### 4.2 커밋 메시지 컨벤션

**형식**:

```
{type}({scope}): {subject}

{body}   (선택)

{footer} (선택)
```

**type 목록**:

| type | 용도 |
|------|------|
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 기능 변경 없는 코드 구조 개선 |
| `test` | 테스트 코드 추가/수정 |
| `docs` | 문서 작성/수정 |
| `style` | 코드 포맷팅 (기능 변경 없음) |
| `chore` | 빌드 설정, 의존성 업데이트 등 |
| `perf` | 성능 개선 |

**scope 예시**: `auth`, `place`, `category`, `stats`, `map`, `common`, `config`

**subject 규칙**:
- 한글 또는 영어 사용 가능 (팀 내 혼용 허용, 단 일관성 유지)
- 명령형 동사로 시작 (한글: "~구현", "~수정", "~추가" / 영어: "add", "fix", "update")
- 마침표 사용 금지
- 50자 이내

**커밋 메시지 예시**:

```
feat(auth): JWT 로그인 API 구현

- POST /api/v1/auth/login 엔드포인트 추가
- Access Token (30분) + Refresh Token (7일) 발급
- Refresh Token HttpOnly Cookie 설정

Closes #FP-001
```

```
fix(place): 삭제된 장소 조회 시 404 대신 200 반환되는 버그 수정
```

```
refactor(common): ApiResponse 빌더 패턴으로 개선
```

### 4.3 코드 리뷰 기준 (DevLead 체크 항목)

**필수 검토 항목**:

| 분류 | 체크 항목 |
|------|----------|
| API 규약 | `ApiResponse<T>` 포맷 준수 여부 |
| API 규약 | HTTP 상태 코드 적절성 |
| API 규약 | ErrorCode enum 기반 예외 처리 여부 |
| 보안 | 인증/인가 처리 누락 여부 |
| 보안 | 타 사용자 데이터 접근 차단 여부 |
| 성능 | N+1 쿼리 발생 여부 |
| 성능 | 불필요한 전체 조회 (findAll) 사용 여부 |
| 네이밍 | 컨벤션 준수 여부 |
| 트랜잭션 | @Transactional 누락 또는 잘못된 적용 여부 |
| 유효성 | @Valid + 유효성 어노테이션 적용 여부 |

---

*문서 끝 - 본 문서는 전체 개발자에게 공유하며, 변경 사항은 DevLead 승인 후 반영한다.*
