# Shelfy - 개발 표준 가이드

- 작성일: 2026-05-09
- 작성자: DevLead
- 버전: v1.0.0

---

## 목차

1. [API 공통 요청/응답 포맷](#1-api-공통-요청응답-포맷)
2. [공통 에러 코드 체계](#2-공통-에러-코드-체계)
3. [커밋 메시지 컨벤션](#3-커밋-메시지-컨벤션)
4. [PR 리뷰 기준](#4-pr-리뷰-기준)
5. [코드 스타일 가이드 - Backend (Java)](#5-코드-스타일-가이드---backend-java)
6. [코드 스타일 가이드 - Frontend (TypeScript)](#6-코드-스타일-가이드---frontend-typescript)
7. [Git 브랜치 전략](#7-git-브랜치-전략)

---

## 1. API 공통 요청/응답 포맷

### 1.1 Base URL

```
개발: http://localhost:8080/api/v1
스테이징: https://api-dev.shelfy.io/api/v1
운영: https://api.shelfy.io/api/v1
```

### 1.2 공통 요청 헤더

| 헤더명 | 필수 | 설명 |
|---|---|---|
| Content-Type | Y | `application/json` (파일 업로드 시 `multipart/form-data`) |
| Authorization | 조건부 | `Bearer {accessToken}` (인증 필요 API만) |
| Accept-Language | N | `ko` / `en` (기본값: `ko`) |

### 1.3 공통 성공 응답 포맷

**단일 리소스 응답**

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

**목록/페이지네이션 응답**

```json
{
  "success": true,
  "data": {
    "content": [
      { "itemId": 5001, "title": "포토샵 작업 템플릿 50종" },
      { "itemId": 5002, "title": "웹 디자인 키트" }
    ],
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

**응답 바디 없음 (DELETE, 일부 POST)**

```
HTTP 204 No Content
(응답 바디 없음)
```

### 1.4 공통 에러 응답 포맷

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

**유효성 검사 실패 (다중 필드)**

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "COMMON-E001",
    "message": "입력값이 올바르지 않습니다.",
    "details": [
      { "field": "email", "message": "올바른 이메일 형식을 입력하세요." },
      { "field": "password", "message": "비밀번호는 8~20자여야 합니다." }
    ]
  },
  "timestamp": "2026-05-09T12:00:00Z"
}
```

### 1.5 HTTP 상태 코드 기준

| 상태 코드 | 사용 상황 |
|---|---|
| 200 OK | 조회 성공, 수정 성공 |
| 201 Created | 리소스 생성 성공 (회원가입, 상품 등록, 주문 생성 등) |
| 204 No Content | 삭제 성공, 로그아웃 등 응답 바디 없는 성공 |
| 400 Bad Request | 요청 유효성 검사 실패 (형식 오류, 필수값 누락) |
| 401 Unauthorized | 인증 실패 (토큰 없음, 만료, 유효하지 않음) |
| 402 Payment Required | 결제 실패 |
| 403 Forbidden | 인증은 됐으나 권한 없음 (타인 리소스, 이메일 미인증) |
| 404 Not Found | 리소스 없음 |
| 409 Conflict | 중복 데이터 (이메일/닉네임 중복, 이미 구독 중) |
| 422 Unprocessable Entity | 비즈니스 로직 오류 (구독자 있는 상품 삭제 시도 등) |
| 500 Internal Server Error | 서버 내부 오류 |

### 1.6 Backend 구현 예시

**ApiResponse.java**

```java
@Getter
@NoArgsConstructor(access = AccessLevel.PRIVATE)
public class ApiResponse<T> {

    private boolean success;
    private T data;
    private ErrorDetail error;
    private String timestamp;

    public static <T> ApiResponse<T> success(T data) {
        ApiResponse<T> response = new ApiResponse<>();
        response.success = true;
        response.data = data;
        response.error = null;
        response.timestamp = Instant.now().toString();
        return response;
    }

    public static <T> ApiResponse<T> error(String code, String message) {
        ApiResponse<T> response = new ApiResponse<>();
        response.success = false;
        response.data = null;
        response.error = new ErrorDetail(code, message);
        response.timestamp = Instant.now().toString();
        return response;
    }

    @Getter
    @AllArgsConstructor
    public static class ErrorDetail {
        private String code;
        private String message;
    }
}
```

**PageResponse.java**

```java
@Getter
@AllArgsConstructor
public class PageResponse<T> {

    private List<T> content;
    private int page;
    private int size;
    private long totalElements;
    private int totalPages;
    private boolean first;
    private boolean last;

    public static <T> PageResponse<T> of(Page<T> page) {
        return new PageResponse<>(
            page.getContent(),
            page.getNumber(),
            page.getSize(),
            page.getTotalElements(),
            page.getTotalPages(),
            page.isFirst(),
            page.isLast()
        );
    }
}
```

**Controller 작성 예시**

```java
@RestController
@RequestMapping("/api/v1/items")
@RequiredArgsConstructor
public class ItemController {

    private final ItemService itemService;

    @PostMapping
    public ResponseEntity<ApiResponse<CreateItemResponse>> createItem(
            @RequestBody @Valid CreateItemRequest request,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        CreateItemResponse response = itemService.createItem(request, userDetails.getUserId());
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success(response));
    }

    @GetMapping("/{itemId}")
    public ResponseEntity<ApiResponse<ItemDetailResponse>> getItem(
            @PathVariable Long itemId) {
        ItemDetailResponse response = itemService.getItemDetail(itemId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<ItemSummaryResponse>>> getItems(
            @ModelAttribute ItemSearchCondition condition) {
        PageResponse<ItemSummaryResponse> response = itemService.getItems(condition);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @DeleteMapping("/{itemId}")
    public ResponseEntity<Void> deleteItem(
            @PathVariable Long itemId,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        itemService.deleteItem(itemId, userDetails.getUserId());
        return ResponseEntity.noContent().build();
    }
}
```

### 1.7 Frontend API 클라이언트 예시

**lib/api/client.ts**

```typescript
import axios, { AxiosInstance } from 'axios';
import { useAuthStore } from '@/stores/authStore';

const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // refreshToken 쿠키 자동 포함
});

// 요청 인터셉터: Access Token 자동 삽입
apiClient.interceptors.request.use((config) => {
  const accessToken = useAuthStore.getState().accessToken;
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// 응답 인터셉터: 401 시 토큰 갱신 후 재시도
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const { data } = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/auth/token/refresh`,
          {},
          { withCredentials: true }
        );
        const newToken = data.data.accessToken;
        useAuthStore.getState().setAccessToken(newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch {
        useAuthStore.getState().clearAuth();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

**types/api.ts**

```typescript
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  timestamp: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: FieldError[];
}

export interface FieldError {
  field: string;
  message: string;
}

export interface PageResponse<T> {
  content: T[];
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
  first: boolean;
  last: boolean;
}
```

---

## 2. 공통 에러 코드 체계

### 2.1 에러 코드 명명 규칙

```
{도메인}-{E/I}{순번}

E: External Error (클라이언트 요인)
I: Internal Error (서버 요인)

예시:
  AUTH-E001  : 인증 도메인, 클라이언트 오류, 001번
  ITEM-E020  : 상품 도메인, 클라이언트 오류, 020번
  COMMON-I001: 공통 도메인, 서버 내부 오류, 001번
```

### 2.2 공통 에러 코드

| 에러 코드 | HTTP | 설명 |
|---|---|---|
| COMMON-E001 | 400 | 입력값 유효성 검사 실패 |
| COMMON-E002 | 401 | 인증 토큰 없음 |
| COMMON-E003 | 403 | 접근 권한 없음 |
| COMMON-E004 | 404 | 리소스 없음 |
| COMMON-I001 | 500 | 서버 내부 오류 |

### 2.3 인증(AUTH) 에러 코드

| 에러 코드 | HTTP | 설명 | 응답 메시지 |
|---|---|---|---|
| AUTH-E001 | 409 | 이메일 중복 | 이미 사용 중인 이메일입니다. |
| AUTH-E002 | 409 | 닉네임 중복 | 이미 사용 중인 닉네임입니다. |
| AUTH-E003 | 400 | 비밀번호 불일치 | 비밀번호가 일치하지 않습니다. |
| AUTH-E004 | 400 | 이메일 형식 오류 | 올바른 이메일 형식을 입력하세요. |
| AUTH-E005 | 400 | 비밀번호 규칙 위반 | 비밀번호는 8~20자, 영문·숫자·특수문자를 포함해야 합니다. |
| AUTH-E006 | 400 | 필수 동의 누락 | 필수 약관에 동의해야 합니다. |
| AUTH-E010 | 400 | 이메일 인증 토큰 만료 | 인증 링크가 만료되었습니다. 재발송을 요청하세요. |
| AUTH-E011 | 400 | 유효하지 않은 인증 토큰 | 유효하지 않은 인증 링크입니다. |
| AUTH-E012 | 409 | 이미 인증 완료 | 이미 이메일 인증이 완료된 계정입니다. |
| AUTH-E020 | 401 | 이메일 미존재 또는 비밀번호 불일치 | 이메일 또는 비밀번호를 확인하세요. |
| AUTH-E021 | 403 | 계정 잠금 | 로그인 5회 실패로 계정이 잠금되었습니다. 30분 후 재시도하거나 비밀번호를 재설정하세요. |
| AUTH-E022 | 403 | 탈퇴된 계정 | 탈퇴된 계정입니다. |
| AUTH-E030 | 401 | Refresh Token 만료 | 세션이 만료되었습니다. 다시 로그인하세요. |
| AUTH-E031 | 401 | 유효하지 않은 Refresh Token | 인증 정보가 유효하지 않습니다. 다시 로그인하세요. |

### 2.4 상품(ITEM) 에러 코드

| 에러 코드 | HTTP | 설명 | 응답 메시지 |
|---|---|---|---|
| ITEM-E001 | 403 | 이메일 미인증 | 이메일 인증 후 상품을 등록할 수 있습니다. |
| ITEM-E002 | 400 | 이미지 형식 오류 | JPG, PNG, WEBP 형식의 이미지만 업로드 가능합니다. |
| ITEM-E003 | 400 | 이미지 용량 초과 | 이미지 1장당 최대 10MB까지 업로드 가능합니다. |
| ITEM-E004 | 400 | 이미지 개수 초과 | 이미지는 최대 10장까지 등록 가능합니다. |
| ITEM-E005 | 400 | 가격 범위 오류 | 가격은 100원 이상 10,000,000원 이하여야 합니다. |
| ITEM-E006 | 400 | 유효하지 않은 카테고리 | 유효하지 않은 카테고리입니다. |
| ITEM-E007 | 400 | 구독 플랜 누락 | 구독 상품은 최소 1개의 플랜을 설정해야 합니다. |
| ITEM-E020 | 403 | 상품 수정 권한 없음 | 해당 상품을 수정할 권한이 없습니다. |
| ITEM-E021 | 422 | 구독자 존재하는 플랜 가격 변경 | 구독자가 있는 플랜의 가격은 변경할 수 없습니다. |
| ITEM-E022 | 404 | 상품 없음 | 상품을 찾을 수 없습니다. |
| ITEM-E030 | 422 | 활성 구독자 있는 상품 삭제 | 활성 구독자가 있는 상품은 삭제할 수 없습니다. |
| ITEM-E031 | 403 | 상품 삭제 권한 없음 | 해당 상품을 삭제할 권한이 없습니다. |

### 2.5 탐색(BROWSE) 에러 코드

| 에러 코드 | HTTP | 설명 | 응답 메시지 |
|---|---|---|---|
| BROWSE-E001 | 404 | 상품 없음 | 상품을 찾을 수 없습니다. |
| BROWSE-E002 | 403 | 비공개 상품 접근 | 비공개 상품입니다. |

### 2.6 주문(ORDER) 에러 코드

| 에러 코드 | HTTP | 설명 | 응답 메시지 |
|---|---|---|---|
| ORDER-E001 | 422 | 본인 상품 구매 | 본인 상품은 구매할 수 없습니다. |
| ORDER-E002 | 404 | 상품 없음 또는 비공개 | 구매할 수 없는 상품입니다. |
| ORDER-E003 | 402 | 결제 실패 | 결제에 실패했습니다. 잠시 후 다시 시도하세요. |
| ORDER-E004 | 422 | 구독 전용 상품 구매 시도 | 해당 상품은 구독으로만 이용 가능합니다. |
| ORDER-E010 | 422 | 환불 기간 초과 | 구매 후 7일이 경과하여 환불이 불가합니다. |
| ORDER-E011 | 422 | 콘텐츠 열람 이력 존재 | 콘텐츠 열람 이력이 있어 환불이 불가합니다. |

### 2.7 구독(SUB) 에러 코드

| 에러 코드 | HTTP | 설명 | 응답 메시지 |
|---|---|---|---|
| SUB-E001 | 409 | 이미 활성 구독 중 | 이미 해당 상품을 구독 중입니다. |
| SUB-E002 | 422 | 본인 상품 구독 | 본인 상품은 구독할 수 없습니다. |
| SUB-E003 | 422 | 구독 미지원 상품 | 해당 상품은 구독을 지원하지 않습니다. |
| SUB-E004 | 402 | 결제 실패 | 결제에 실패했습니다. 결제 수단을 확인하세요. |

### 2.8 Backend ErrorCode Enum 구현

```java
@Getter
@RequiredArgsConstructor
public enum ErrorCode {

    // 공통
    INVALID_INPUT(HttpStatus.BAD_REQUEST, "COMMON-E001", "입력값이 올바르지 않습니다."),
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED, "COMMON-E002", "인증이 필요합니다."),
    FORBIDDEN(HttpStatus.FORBIDDEN, "COMMON-E003", "접근 권한이 없습니다."),
    RESOURCE_NOT_FOUND(HttpStatus.NOT_FOUND, "COMMON-E004", "리소스를 찾을 수 없습니다."),
    INTERNAL_SERVER_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "COMMON-I001", "서버 내부 오류가 발생했습니다."),

    // 인증
    EMAIL_DUPLICATED(HttpStatus.CONFLICT, "AUTH-E001", "이미 사용 중인 이메일입니다."),
    NICKNAME_DUPLICATED(HttpStatus.CONFLICT, "AUTH-E002", "이미 사용 중인 닉네임입니다."),
    PASSWORD_MISMATCH(HttpStatus.BAD_REQUEST, "AUTH-E003", "비밀번호가 일치하지 않습니다."),
    LOGIN_FAILED(HttpStatus.UNAUTHORIZED, "AUTH-E020", "이메일 또는 비밀번호를 확인하세요."),
    ACCOUNT_LOCKED(HttpStatus.FORBIDDEN, "AUTH-E021", "계정이 잠금되었습니다. 30분 후 재시도하거나 비밀번호를 재설정하세요."),
    REFRESH_TOKEN_EXPIRED(HttpStatus.UNAUTHORIZED, "AUTH-E030", "세션이 만료되었습니다. 다시 로그인하세요."),
    REFRESH_TOKEN_INVALID(HttpStatus.UNAUTHORIZED, "AUTH-E031", "인증 정보가 유효하지 않습니다. 다시 로그인하세요."),

    // 상품
    EMAIL_NOT_VERIFIED(HttpStatus.FORBIDDEN, "ITEM-E001", "이메일 인증 후 상품을 등록할 수 있습니다."),
    ITEM_NOT_FOUND(HttpStatus.NOT_FOUND, "ITEM-E022", "상품을 찾을 수 없습니다."),
    ITEM_FORBIDDEN(HttpStatus.FORBIDDEN, "ITEM-E020", "해당 상품을 수정할 권한이 없습니다."),
    ACTIVE_SUBSCRIBER_EXISTS(HttpStatus.UNPROCESSABLE_ENTITY, "ITEM-E030", "활성 구독자가 있는 상품은 삭제할 수 없습니다."),

    // 주문
    SELF_PURCHASE(HttpStatus.UNPROCESSABLE_ENTITY, "ORDER-E001", "본인 상품은 구매할 수 없습니다."),
    PAYMENT_FAILED(HttpStatus.PAYMENT_REQUIRED, "ORDER-E003", "결제에 실패했습니다."),

    // 구독
    ALREADY_SUBSCRIBED(HttpStatus.CONFLICT, "SUB-E001", "이미 해당 상품을 구독 중입니다."),
    SELF_SUBSCRIPTION(HttpStatus.UNPROCESSABLE_ENTITY, "SUB-E002", "본인 상품은 구독할 수 없습니다.");

    private final HttpStatus httpStatus;
    private final String code;
    private final String message;
}
```

---

## 3. 커밋 메시지 컨벤션

### 3.1 형식

```
<type>(<scope>): <subject>

[body - 선택사항]

[footer - 선택사항]
```

### 3.2 Type 정의

| Type | 설명 | 예시 상황 |
|---|---|---|
| feat | 새로운 기능 추가 | 상품 등록 API 구현 |
| fix | 버그 수정 | 토큰 만료 처리 오류 수정 |
| refactor | 기능 변경 없는 코드 리팩토링 | Service 레이어 구조 개선 |
| style | 코드 포맷, 공백 등 (로직 변경 없음) | 코드 정렬, 불필요한 공백 제거 |
| test | 테스트 코드 추가/수정 | 회원가입 단위 테스트 추가 |
| docs | 문서 수정 | API 명세 주석 추가 |
| chore | 빌드, 의존성, 설정 변경 | build.gradle 의존성 추가 |
| perf | 성능 개선 | 상품 목록 쿼리 인덱스 적용 |
| ci | CI/CD 설정 변경 | GitHub Actions workflow 추가 |

### 3.3 Scope 정의

| Scope | 대상 |
|---|---|
| auth | 인증/인가 관련 |
| item | 상품 관련 |
| order | 주문/결제 관련 |
| subscription | 구독 관련 |
| user | 사용자/프로필 관련 |
| file | 파일 업로드 관련 |
| common | 공통 모듈 |
| infra | 인프라, Docker, CI/CD |
| db | 데이터베이스 마이그레이션 |

### 3.4 규칙

- subject는 50자 이내, 명령문 형태 (동사 원형), 마침표 없음
- body는 72자 줄바꿈, "무엇을" 보다 "왜" 중심으로 작성
- footer에 Jira 이슈 번호 기재: `Refs: SHF-123`
- 영문 소문자 사용 (고유명사 제외)

### 3.5 작성 예시

**단순 기능 추가**

```
feat(auth): implement JWT refresh token rotation
```

**버그 수정 + 상세 설명**

```
fix(item): prevent price update when active subscribers exist

구독자가 존재하는 플랜의 가격 변경 시도 시 422 에러를 반환하도록 수정.
기존 코드는 구독자 존재 여부 확인 없이 가격을 업데이트하는 문제가 있었음.

Refs: SHF-142
```

**리팩토링**

```
refactor(common): extract ApiResponse wrapper to shared module

각 도메인 Controller에 분산되어 있던 응답 생성 로직을 
ApiResponse 공통 클래스로 통합.
```

---

## 4. PR 리뷰 기준

### 4.1 PR 생성 규칙

- PR 제목: `[타입] 간략한 변경 내용 설명` (예: `[feat] 상품 등록 API 구현`)
- PR 본문에 반드시 포함할 항목:
  1. 변경 사항 요약 (What)
  2. 변경 이유 (Why)
  3. 테스트 방법 (How to test)
  4. 관련 Jira 이슈 번호
- 1 PR = 1 기능/버그 원칙 (범위 혼합 금지)
- PR 크기: 변경 파일 10개 이하, diff 500줄 이하 권고 (초과 시 DevLead와 분할 협의)

### 4.2 PR 리뷰 체크리스트 (DevLead)

**필수 검토 항목 (Blocking)**

```
[ ] API 공통 응답 포맷(ApiResponse) 준수 여부
[ ] 에러 코드 체계(ErrorCode Enum) 사용 여부
[ ] 트랜잭션 경계 적절성 (@Transactional 범위)
[ ] 인증/인가 검증 누락 여부
[ ] SQL Injection 취약점 (MyBatis: #{} 사용 여부)
[ ] 민감 정보 로그 노출 여부 (비밀번호, 토큰)
[ ] N+1 쿼리 발생 가능성
[ ] 입력값 유효성 검사 (@Valid, @NotBlank 등)
```

**권고 검토 항목 (Non-blocking)**

```
[ ] 메서드/클래스 명명이 역할을 명확히 표현하는가
[ ] 불필요한 주석 또는 주석 처리된 코드 존재 여부
[ ] 하드코딩된 매직 넘버/문자열
[ ] 단위 테스트 존재 여부 (Service 레이어 이상)
[ ] 예외 처리 누락된 엣지 케이스
[ ] 코드 중복 (DRY 원칙)
```

### 4.3 리뷰 코멘트 규칙

| 레이블 | 의미 | 머지 가능 여부 |
|---|---|---|
| `[Blocking]` | 반드시 수정 후 머지 | 수정 전 머지 불가 |
| `[Suggestion]` | 개선 권고, 작성자 판단 | 현재 상태로 머지 가능 |
| `[Question]` | 의도 확인 질문 | 답변 후 머지 가능 |
| `[Nit]` | 사소한 스타일/오타 | 즉시 머지 가능 |

**코멘트 예시**

```
[Blocking] 
서비스 레이어에서 직접 HttpStatus를 참조하고 있습니다.
HTTP 상태 코드는 Controller 레이어 책임입니다.
ErrorCode Enum으로 교체해 주세요.

[Suggestion]
이 메서드는 3가지 책임을 갖고 있습니다 (검증, 조회, 저장).
가독성을 위해 private 메서드로 분리를 고려해 주세요.

[Nit]
변수명 `tmp` -> `itemThumbnail` 처럼 의미 있는 이름 권장합니다.
```

### 4.4 머지 조건

- Blocking 코멘트 전량 해소
- DevLead Approve 1개 이상
- CI/CD 파이프라인 통과 (빌드, 린트, 단위 테스트)
- 대상 브랜치 기준 충돌 없음

---

## 5. 코드 스타일 가이드 - Backend (Java)

### 5.1 기본 원칙

- Google Java Style Guide 준수
- IntelliJ IDEA 기본 포맷터 설정 사용
- 탭 대신 스페이스 4칸 사용

### 5.2 명명 규칙

```java
// 클래스: PascalCase
public class ItemService { }
public class CreateItemRequest { }

// 메서드, 변수: camelCase
public ItemDetailResponse getItemDetail(Long itemId) { }
private String accessToken;

// 상수: UPPER_SNAKE_CASE
private static final int MAX_LOGIN_ATTEMPT = 5;
private static final long TOKEN_EXPIRATION_SECONDS = 3600L;

// 패키지: 소문자, 단수
package com.shelfy.item.service;
package com.shelfy.auth.dto.request;

// Enum: PascalCase (상수값은 UPPER_SNAKE_CASE)
public enum SaleType { PURCHASE, SUBSCRIBE, BOTH }
public enum ItemStatus { DRAFT, PUBLISHED }
```

### 5.3 어노테이션 규칙

```java
// DTO: Lombok 활용, Builder 패턴 적용
@Getter
@Builder
@NoArgsConstructor(access = AccessLevel.PRIVATE)
@AllArgsConstructor
public class CreateItemResponse {
    private Long itemId;
}

// Entity: JPA + Lombok
@Entity
@Table(name = "items")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED) // JPA 프록시 요구사항
public class Item {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // setter 직접 노출 금지, 도메인 메서드로 상태 변경
    public void updateStatus(ItemStatus status) {
        this.status = status;
        this.updatedAt = LocalDateTime.now();
    }
}

// Service: 트랜잭션 기본 readOnly
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class ItemService {

    @Transactional // 쓰기 작업만 별도 선언
    public CreateItemResponse createItem(CreateItemRequest request, Long sellerId) {
        // ...
    }

    public ItemDetailResponse getItemDetail(Long itemId) {
        // readOnly 상속
    }
}
```

### 5.4 예외 처리

```java
// 커스텀 예외: ErrorCode 포함
public class ShelfyException extends RuntimeException {

    private final ErrorCode errorCode;

    public ShelfyException(ErrorCode errorCode) {
        super(errorCode.getMessage());
        this.errorCode = errorCode;
    }
}

// 사용 예시
if (item.getSellerId().equals(buyerId)) {
    throw new ShelfyException(ErrorCode.SELF_PURCHASE);
}

// 전역 예외 처리
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ShelfyException.class)
    public ResponseEntity<ApiResponse<Void>> handleShelfyException(ShelfyException e) {
        ErrorCode errorCode = e.getErrorCode();
        return ResponseEntity
                .status(errorCode.getHttpStatus())
                .body(ApiResponse.error(errorCode.getCode(), errorCode.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidationException(
            MethodArgumentNotValidException e) {
        // 유효성 검사 실패 필드 목록 반환
    }
}
```

### 5.5 금지 사항

```java
// 금지: System.out.println 사용 (SLF4J Logger 사용)
System.out.println("item: " + item); // 금지

// 허용
private static final Logger log = LoggerFactory.getLogger(ItemService.class);
log.info("Item created: itemId={}, sellerId={}", item.getId(), sellerId);

// 금지: 비밀번호, 토큰 로그 출력
log.info("User login: password={}", password); // 절대 금지

// 금지: Entity를 Response DTO로 그대로 반환
return ResponseEntity.ok(item); // 금지 (Entity 직접 노출)

// 허용
return ResponseEntity.ok(ApiResponse.success(ItemDetailResponse.from(item)));

// 금지: MyBatis ${}로 값 삽입 (SQL Injection 위험)
// ItemMapper.xml
SELECT * FROM items WHERE title LIKE '%${keyword}%' -- 금지
SELECT * FROM items WHERE title LIKE '%' || #{keyword} || '%' -- 허용
```

---

## 6. 코드 스타일 가이드 - Frontend (TypeScript)

### 6.1 기본 설정

- ESLint: Next.js 기본 규칙 + `@typescript-eslint/recommended`
- Prettier: 2스페이스 들여쓰기, 싱글쿼트, 세미콜론 없음
- TypeScript strict 모드 활성화 (`"strict": true`)

### 6.2 명명 규칙

```typescript
// 컴포넌트: PascalCase
export function ItemCard({ item }: ItemCardProps) {}
export default function ItemDetailPage() {}

// 훅: camelCase, use 접두사
export function useItems(condition: ItemSearchCondition) {}
export function useAuth() {}

// 타입/인터페이스: PascalCase
interface ItemDetailResponse {
  itemId: number;
  title: string;
}

type SaleType = 'PURCHASE' | 'SUBSCRIBE' | 'BOTH';

// 상수: UPPER_SNAKE_CASE
const MAX_IMAGE_SIZE_MB = 10;
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

// 파일명
// 컴포넌트: PascalCase (ItemCard.tsx)
// 훅: camelCase (useItems.ts)
// 유틸: camelCase (formatters.ts)
// 타입: camelCase (item.ts)
// 페이지: page.tsx (Next.js App Router 규칙)
```

### 6.3 컴포넌트 작성 규칙

```typescript
// Props 타입은 컴포넌트 바로 위에 정의
interface ItemCardProps {
  item: ItemSummaryResponse;
  onClick?: (itemId: number) => void;
  className?: string;
}

// 함수형 컴포넌트, export function 방식 (default export는 page.tsx에만)
export function ItemCard({ item, onClick, className }: ItemCardProps) {
  const handleClick = () => {
    onClick?.(item.itemId);
  };

  return (
    <div className={cn('rounded-lg border', className)} onClick={handleClick}>
      <span>{item.title}</span>
    </div>
  );
}

// 서버 컴포넌트 vs 클라이언트 컴포넌트 명시
// 'use client'가 없으면 기본적으로 서버 컴포넌트
// 클라이언트 상호작용(useState, onClick, useEffect) 필요 시에만 'use client' 추가
'use client';

export function LoginForm() {
  const [email, setEmail] = useState('');
  // ...
}
```

### 6.4 TanStack Query 사용 규칙

```typescript
// hooks/useItems.ts
// Query Key 상수화
export const itemQueryKeys = {
  all: ['items'] as const,
  lists: () => [...itemQueryKeys.all, 'list'] as const,
  list: (condition: ItemSearchCondition) =>
    [...itemQueryKeys.lists(), condition] as const,
  detail: (itemId: number) =>
    [...itemQueryKeys.all, 'detail', itemId] as const,
};

// 조회 훅
export function useItemDetail(itemId: number) {
  return useQuery({
    queryKey: itemQueryKeys.detail(itemId),
    queryFn: () => fetchItemDetail(itemId),
    enabled: !!itemId,
    staleTime: 60 * 1000, // 1분
  });
}

// 변이 훅
export function useCreateItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: CreateItemRequest) => createItem(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() });
    },
    onError: (error: ApiError) => {
      console.error('상품 등록 실패:', error.code, error.message);
    },
  });
}
```

### 6.5 타입 안전성 규칙

```typescript
// 금지: any 타입 사용
const data: any = await fetchItem(); // 금지

// 허용: unknown + 타입 가드
const data: unknown = await fetchItem();
if (isItemDetailResponse(data)) { /* ... */ }

// 금지: 타입 단언 남용 (as)
const item = data as ItemDetailResponse; // 근거 없는 단언 금지

// API 응답은 반드시 ApiResponse<T> 타입 사용
async function fetchItemDetail(itemId: number): Promise<ItemDetailResponse> {
  const response = await apiClient.get<ApiResponse<ItemDetailResponse>>(
    `/items/${itemId}`
  );
  if (!response.data.success || !response.data.data) {
    throw new Error(response.data.error?.message ?? '조회 실패');
  }
  return response.data.data;
}

// 금지: 환경변수 non-null 단언 (빌드 시 검증)
const apiUrl = process.env.NEXT_PUBLIC_API_URL!; // 단언 금지

// 허용: 런타임 검증
const apiUrl = process.env.NEXT_PUBLIC_API_URL;
if (!apiUrl) throw new Error('NEXT_PUBLIC_API_URL 환경변수가 설정되지 않았습니다.');
```

### 6.6 금지 사항

```typescript
// 금지: 직접 fetch 사용 (apiClient 사용)
const res = await fetch('/api/v1/items'); // 금지

// 금지: 토큰 localStorage 저장
localStorage.setItem('accessToken', token); // 보안 위협, 절대 금지

// 금지: console.log 커밋 (개발 디버깅 후 제거)
console.log('item:', item); // 커밋 전 제거 필수

// 금지: 인라인 스타일 (Tailwind CSS 클래스 사용)
<div style={{ color: 'red' }}>내용</div> // 금지
<div className="text-red-500">내용</div> // 허용
```

---

## 7. Git 브랜치 전략

### 7.1 브랜치 구조

```
main              # 운영 배포 브랜치 (직접 push 금지)
develop           # 개발 통합 브랜치 (PR 머지 대상)
feature/*         # 기능 개발 브랜치
fix/*             # 버그 수정 브랜치
hotfix/*          # 운영 긴급 패치 브랜치
release/*         # 배포 준비 브랜치 (QA 검증)
```

### 7.2 브랜치 명명 규칙

```
feature/{Jira이슈번호}-{간략설명}
fix/{Jira이슈번호}-{간략설명}
hotfix/{Jira이슈번호}-{간략설명}
release/v{버전번호}

예시:
feature/SHF-101-auth-signup-api
feature/SHF-115-item-create-api
fix/SHF-142-item-price-update-bug
hotfix/SHF-200-login-500-error
release/v1.0.0
```

### 7.3 작업 흐름

```
1. develop에서 feature 브랜치 생성
   git checkout develop
   git pull origin develop
   git checkout -b feature/SHF-101-auth-signup-api

2. 개발 및 커밋

3. develop으로 PR 생성
   - PR 제목: [feat] 회원가입 API 구현 (SHF-101)
   - DevLead 리뷰 요청

4. 리뷰 통과 후 Squash Merge to develop
   (커밋 히스토리 정리)

5. 배포 준비 시 release 브랜치 생성
   git checkout -b release/v1.0.0 develop

6. QA 완료 후 main 머지 + 태그
   git tag v1.0.0
```

### 7.4 보호 규칙 (Branch Protection)

| 브랜치 | 직접 Push | PR 필수 | 리뷰 필수 | CI 통과 필수 |
|---|---|---|---|---|
| main | 금지 | 필수 | DevLead Approve | 필수 |
| develop | 금지 | 필수 | DevLead Approve | 필수 |
| release/* | 금지 | 필수 | DevLead Approve | 필수 |
| feature/* | 허용 | - | - | - |
| fix/* | 허용 | - | - | - |
