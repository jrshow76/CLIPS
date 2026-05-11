# API 표준 (API Standards)

| 항목 | 내용 |
|---|---|
| 문서명 | Tulip+ API 설계 규약 |
| 문서 ID | DEV-03 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | DevLead Agent |
| 검토자 | PM, BackendSenior, FrontendSenior, QA |
| 입력 | `01_architecture_overview.md`, `02_service_decomposition.md`, Planner 도메인 요구사항 |
| 후속 | OpenAPI 3.x 스펙 (서비스별), `04_error_codes.md` |
| 상태 | Phase 0 초안 |

---

## 1. 적용 범위

본 문서는 Tulip+ 모든 REST API에 의무 적용된다. 위반 시 PR 단계에서 DevLead가 반려한다.

| 대상 | 적용 |
|---|---|
| 모든 마이크로서비스 (15개 + BFF 2 + GW 2) | **필수** |
| 외부 시스템 연동 어댑터(External GW) | 외부 표준은 그대로, 내부 노출은 본 표준 |
| 키오스크/하드웨어 SIP2/NCIP | SIP2/NCIP 표준 우선, 내부 API는 본 표준 |
| OpenAPI 3.x 문서화 | **필수** (CI에서 검증) |
| GraphQL/gRPC 도입 | Y2 이후 별도 검토 |

---

## 2. URL 컨벤션

### 2.1 기본 패턴

```
{scheme}://{host}/api/v{major}/{domain}/{resource}[/{id}][/{sub-resource}]
```

| 구성 요소 | 규칙 | 예시 |
|---|---|---|
| scheme | `https` 의무 | https |
| host | 환경별 도메인 | api.tulip.example.com |
| `api` | 고정 prefix | api |
| `v{major}` | 메이저 버전 | v1, v2 |
| `domain` | 6+1 도메인 약어 (소문자) | cmn, acq, cat, cir, col, acs, fac, opac, stats |
| `resource` | **복수형 명사, 케밥-케이스** | members, bibs, purchase-orders |
| `id` | URI에 노출 가능한 안전한 ID | UUIDv7 또는 BIGINT |

### 2.2 URL 작성 규칙

| 규칙 | 좋은 예 | 나쁜 예 |
|---|---|---|
| 복수형 명사 | `/members` | `/member`, `/getMembers` |
| 동사 금지 (CRUD는 HTTP method) | `POST /loans` | `POST /createLoan` |
| 케밥-케이스 | `/purchase-orders` | `/purchase_orders`, `/PurchaseOrders` |
| 계층은 2단계까지 | `/orders/{id}/items` | `/tenants/{t}/branches/{b}/orders/{o}/items` (Path Param에 tenantId 금지) |
| 동작(action)은 sub-resource | `POST /loans/{id}/renewals` | `POST /loans/{id}/renew` |
| 검색은 GET + 쿼리, 복잡하면 POST + body | `GET /bibs?q=...` 또는 `POST /bibs/search` | - |
| ID는 path, 필터는 query | `/members/{id}?fields=name` | `/members?id=123` |

### 2.3 도메인별 base path

| 도메인 | base path | 책임 서비스 |
|---|---|---|
| 공통 (인증·테넌트·회원·코드·정책·알림) | `/api/v1/auth`, `/api/v1/tenants`, `/api/v1/branches`, `/api/v1/members`, `/api/v1/codes`, `/api/v1/policies`, `/api/v1/notifications` | IAM, Tenant, Member, Code/Policy, Notification |
| 수서 | `/api/v1/acq/*` | Acquisition |
| 목록 | `/api/v1/cat/*` | Catalog |
| 열람 | `/api/v1/cir/*` | Circulation |
| 장서관리 | `/api/v1/col/*` | Collection |
| 출입 | `/api/v1/acs/*` | Access |
| 시설 | `/api/v1/fac/*` | Facility |
| OPAC | `/api/v1/opac/*` | OPAC BFF + Search |
| 통계·리포트 | `/api/v1/stats/*`, `/api/v1/reports/*` | Stats/Report |
| 파일 | `/api/v1/files/*` | File |
| 내부 전용 | `/internal/*` | 서비스 간 호출 (외부 노출 금지) |
| 디바이스 전용 | `/device/*` | 키오스크·게이트 (디바이스 토큰 인증) |

---

## 3. HTTP Method · 상태 코드 표준

### 3.1 메소드 사용 규칙

| Method | 용도 | 멱등성 | 안전성 | 예시 |
|---|---|---|---|---|
| GET | 조회 | O | O | `GET /members/{id}` |
| POST | 생성 / 비멱등 동작 | X | X | `POST /loans` |
| PUT | 전체 교체 (멱등) | O | X | `PUT /bibs/{id}` (KORMARC 전체 교체) |
| PATCH | 부분 변경 | △ | X | `PATCH /members/{id}` |
| DELETE | 삭제 (소프트/하드) | O | X | `DELETE /holds/{id}` |
| HEAD | 헤더만 조회 (캐시) | O | O | `HEAD /bibs/{id}` |

### 3.2 상태 코드 표준

| 코드 | 의미 | 사용 |
|---|---|---|
| 200 OK | 조회/수정 성공 | 정상 응답 |
| 201 Created | 자원 생성 성공 | POST 생성. `Location` 헤더 필수 |
| 202 Accepted | 비동기 접수 | 큐에 적재, 폴링 URL 필요 |
| 204 No Content | 본문 없음 | DELETE 성공 |
| 207 Multi-Status | 배치 부분 성공 | 일괄 import |
| 304 Not Modified | 캐시 유효 | ETag 일치 |
| 400 Bad Request | 입력 검증 실패 | 필수값 누락·형식 오류 |
| 401 Unauthorized | 미인증 | 토큰 없음·만료 |
| 403 Forbidden | 권한 없음 | 권한 부족·테넌트 격리 위반 |
| 404 Not Found | 자원 없음 | 존재하지 않는 ID |
| 409 Conflict | 상태/중복 충돌 | 중복 등록, 상태 충돌, ETag 불일치 |
| 410 Gone | 폐기됨 | 만료된 API |
| 422 Unprocessable Entity | 비즈니스 규칙 위반 | 정책 위반(대출권수 등) |
| 423 Locked | 잠금 상태 | 계정 잠금, 서지 잠금 |
| 428 Precondition Required | 조건 헤더 필요 | `If-Match` 없는 수정 |
| 429 Too Many Requests | Rate Limit | `Retry-After` 헤더 |
| 500 Internal Server Error | 서버 오류 | 예외 미처리 |
| 502 Bad Gateway | 업스트림 오류 | 외부 API 실패 (External GW) |
| 503 Service Unavailable | 일시 중단 | 점검·과부하 |
| 504 Gateway Timeout | 업스트림 시간초과 | Z39.50 등 외부 timeout |

### 3.3 도메인 비즈니스 위반 → 422 사용
- 정책 위반(`CIR-E001` 대출권수 초과, `FAC-E003` 이용 한도 초과 등)은 **422**.
- 단순 상태 충돌(이미 반납됨, 중복 예약)은 **409**.

---

## 4. 공통 요청/응답 포맷

### 4.1 응답 Envelope

모든 정상 응답·에러 응답은 동일한 envelope를 사용한다.

#### 성공 응답 (단건)

```json
{
  "success": true,
  "code": "OK",
  "message": "처리되었습니다",
  "data": {
    "id": "01H9X...",
    "name": "홍길동"
  },
  "meta": {
    "tenantId": "tnt_001",
    "branchId": "br_main"
  },
  "timestamp": "2026-05-11T14:00:00.123+09:00",
  "traceId": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
}
```

#### 성공 응답 (목록 + 페이지네이션)

```json
{
  "success": true,
  "code": "OK",
  "data": [ { "id": "...", "name": "..." } ],
  "meta": {
    "tenantId": "tnt_001",
    "page": {
      "type": "offset",
      "number": 1,
      "size": 20,
      "totalElements": 12345,
      "totalPages": 618
    },
    "sort": ["createdAt,desc"],
    "filter": { "status": "ACTIVE" }
  },
  "timestamp": "2026-05-11T14:00:00.123+09:00",
  "traceId": "..."
}
```

#### 에러 응답

```json
{
  "success": false,
  "code": "TLP-CIR-422-0001",
  "message": "대출 권수 한도를 초과했습니다",
  "userMessage": "현재 대출 가능 권수를 초과했습니다. 반납 후 다시 시도해 주세요.",
  "fieldErrors": [
    { "field": "items[0].itemId", "message": "이미 대출 중인 자료입니다", "rejectedValue": "01H9X..." }
  ],
  "debug": {
    "exception": "LoanLimitExceededException",
    "service": "circulation-service",
    "policyId": "POL-CIR-001",
    "currentLoans": 10,
    "maxLoans": 10
  },
  "timestamp": "2026-05-11T14:00:00.123+09:00",
  "traceId": "..."
}
```

> **`debug` 블록은 비-운영 환경(dev/stg)에서만 노출**, 운영은 마스킹.

### 4.2 필드 의미

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `success` | boolean | O | true/false |
| `code` | string | O | 응답 코드 (성공은 `OK`, 에러는 `TLP-...`) |
| `message` | string | O | 시스템 메시지 (사서/관리자 대상) |
| `userMessage` | string | △ | 일반 사용자 친화 메시지 (OPAC용) |
| `data` | object/array | △ | 본문 |
| `meta` | object | △ | 페이지네이션·필터·테넌트 컨텍스트 |
| `fieldErrors` | array | △ | 400/422 시 필드별 오류 |
| `debug` | object | △ | 비-운영 진단 정보 |
| `timestamp` | ISO-8601 | O | 서버 시각 (KST `+09:00`) |
| `traceId` | string | O | W3C Trace Context 형식 |

### 4.3 날짜·숫자 표준

| 타입 | 형식 | 예시 |
|---|---|---|
| 날짜시각 | ISO-8601 with TZ | `2026-05-11T14:00:00+09:00` |
| 날짜 | `YYYY-MM-DD` | `2026-05-11` |
| 시각 | `HH:mm:ss` | `09:00:00` |
| 금액 | minor unit BIGINT (원 단위 정수) | `12500` (12,500원) |
| 통화 | ISO-4217 | `KRW` |
| 언어 | BCP-47 | `ko-KR`, `en-US` |
| 빈 값 | `null` 사용 (빈 문자열 금지) | - |

### 4.4 필드명 규칙
- JSON: **camelCase**
- DB 컬럼: **snake_case** (DBA 표준)
- ID: `id`(자기) / `xxxId`(외래)
- Boolean: `is`, `has`, `can` prefix 권장

---

## 5. 페이지네이션·정렬·필터링

### 5.1 페이지네이션 두 가지 지원

#### Offset 기반 (기본)

```
GET /api/v1/members?page=1&size=20&sort=createdAt,desc
```

| 파라미터 | 기본 | 최대 | 비고 |
|---|---|---|---|
| `page` | 1 | - | 1-base |
| `size` | 20 | 100 | 초과 시 100으로 캡 |
| `sort` | 도메인별 기본 | - | `field,asc/desc`, 다중 가능 |

#### Cursor 기반 (대용량 / 무한스크롤)

```
GET /api/v1/cir/loans?cursor=eyJpZCI6IjAxSDl...&limit=50
```

| 파라미터 | 비고 |
|---|---|
| `cursor` | base64로 인코딩된 (sort key + tie breaker id) |
| `limit` | 기본 50, 최대 200 |

응답:
```json
"meta": {
  "page": {
    "type": "cursor",
    "limit": 50,
    "next": "eyJpZCI6IjAxSDl..."
  }
}
```

| 적용 가이드 | 사용 페이지네이션 |
|---|---|
| 회원 목록·정책 목록 등 일반 CRUD | Offset |
| 대출 이력·출입 이력·OPAC 검색 결과 | Cursor (성능) |
| 검색(ES) | Cursor + `search_after` |

### 5.2 정렬 (Sort)

- `sort=field,direction[,field2,direction2]`
- 허용 필드는 서비스별 화이트리스트 (OpenAPI에 명시)
- 기본 정렬은 `createdAt,desc` 또는 도메인 특화 (예: 서지 검색 = 관련도)

### 5.3 필터링

| 표현 | 예시 | 비고 |
|---|---|---|
| 단일값 | `?status=ACTIVE` | equals |
| 다중값 (OR) | `?status=ACTIVE,SUSPENDED` | IN |
| 범위 | `?createdAt[gte]=2026-01-01&createdAt[lt]=2026-02-01` | bracket 표기 |
| 부분일치 | `?name[like]=홍길` | 인덱스 영향 → 가용 필드만 |
| 정확 매칭 | `?branchId=br_main` | - |
| 검색어 (텍스트) | `?q=햄릿` | 토큰화 검색 |

> 복잡한 검색은 `POST /xxx/search` body로 제출 (필터 객체).

### 5.4 부분 응답 (Sparse Fieldsets)

```
GET /members/{id}?fields=id,name,memberType,status
```
- 권한 없는 필드는 자동 마스킹/제외 (예: PII).

### 5.5 확장 (Expansion)

```
GET /loans/{id}?expand=member,item.bib
```
- 점(`.`) 표기로 중첩 expansion. 최대 2단계.

---

## 6. 헤더 표준

### 6.1 요청 헤더

| 헤더 | 필수 | 설명 |
|---|---|---|
| `Authorization` | O (인증 API 제외) | `Bearer <JWT>` |
| `Accept` | △ | `application/json` (기본) |
| `Accept-Language` | △ | `ko-KR`, `en-US` (다국어 메시지) |
| `Content-Type` | POST/PUT/PATCH | `application/json; charset=utf-8` |
| `X-Tenant-Id` | 플랫폼 관리자만 | 임의 테넌트 전환 |
| `X-Branch-Id` | △ | 다관 운영 시 현재 관 |
| `X-Trace-Id` | △ | 클라이언트 발급 trace id (없으면 GW가 생성) |
| `X-Request-Id` | △ | 요청 단위 ID |
| `Idempotency-Key` | POST 중요 거래 | 대출/결제/예약 멱등 키 |
| `If-Match` | PUT/PATCH/DELETE 시 권장 | ETag 기반 동시성 제어 |
| `If-None-Match` | GET 캐시 | ETag |
| `User-Agent` | △ | 디바이스/클라이언트 식별 |

### 6.2 응답 헤더

| 헤더 | 설명 |
|---|---|
| `X-Trace-Id` | 요청 trace id 메아리 |
| `X-Request-Id` | 서버 발급 |
| `ETag` | 조회/생성 응답에 자원 버전 |
| `Location` | 201 Created 시 새 자원 URL |
| `Retry-After` | 429/503 시 |
| `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` | Rate Limit 정보 |
| `Cache-Control` | 캐싱 정책 |
| `Content-Language` | 응답 메시지 언어 |

---

## 7. 멱등성·동시성 처리

### 7.1 Idempotency-Key (멱등성)

**대상**: 부작용이 큰 POST (대출, 반납, 결제, 예약, 발주, 검수).

```
POST /api/v1/cir/checkouts
Idempotency-Key: 01H9X-uuid-...
```

서버는 (tenantId + Idempotency-Key) 조합으로 24시간 유지 → 동일 키 재요청은 캐시된 응답 반환.

### 7.2 ETag (낙관적 동시성)

```
GET /api/v1/cat/bibs/{id}
→ 200 OK, ETag: "v3"

PATCH /api/v1/cat/bibs/{id}
If-Match: "v3"

→ 409 Conflict (다른 사용자가 수정)
```

대상: 서지·정책·회원 등 동시 편집 가능 자원.

### 7.3 분산락 (Pessimistic)

- 일반적으로 ETag로 충분.
- 장서점검·관간대차 등 long-running 작업은 Redis 분산락(`SET key NX PX <ttl>`) 사용.

---

## 8. API 버저닝

### 8.1 버전 정책

| 변경 유형 | 버전 변경 | 예시 |
|---|---|---|
| **Breaking** (필드 제거, 타입 변경, URL 변경, 의미 변경) | major bump (`v1→v2`) | KORMARC 응답 구조 변경 |
| **Non-breaking** (필드 추가, 신규 엔드포인트, 옵션 파라미터) | 동일 버전 | 신규 필드 추가 |
| **Deprecation** | 6개월 유예 | `Deprecation`, `Sunset` 헤더 |

### 8.2 다중 버전 운영

- Gateway에서 path 기반 라우팅 (`/api/v1/*` → v1 service, `/api/v2/*` → v2 service).
- 동일 서비스 내부에서 컨트롤러 클래스 분리 (`V1MemberController`, `V2MemberController`).
- v1과 v2는 **최소 12개월 병행 운영**.

### 8.3 Deprecation 헤더

```
Deprecation: true
Sunset: Wed, 31 Dec 2026 23:59:59 GMT
Link: <https://docs.tulip.example.com/v2/migration>; rel="successor-version"
```

---

## 9. 파일 업로드·다운로드

### 9.1 작은 파일 (~10MB)

multipart/form-data 직접 업로드:
```
POST /api/v1/files
Content-Type: multipart/form-data

→ 201 Created, body: { id, url, sha256, size }
```

### 9.2 큰 파일·MARC 일괄 import (>10MB)

**Presigned URL** 패턴:
```
1. POST /api/v1/files/presign
   body: { filename, contentType, size }
→ 200 OK, body: { uploadUrl, fileId, fields, expiresAt }

2. Client → PUT/POST uploadUrl (직접 S3)

3. POST /api/v1/cat/bibs/bulk-import
   body: { fileId }
→ 202 Accepted, body: { jobId, pollUrl }

4. GET /api/v1/jobs/{jobId}
→ 진행률·결과
```

| 적용 | API |
|---|---|
| MARC 파일 import/export | CAT-API-040 |
| 일괄 회원 등록 | CMN-018 |
| 라벨 PDF 다운로드 | COL-API-050 |
| 시설 고장 사진 | FAC-API-020 |

### 9.3 다운로드

- 일반 다운로드: 200 OK + `Content-Disposition: attachment; filename="...";`
- 대량/장시간: 202 + Job → Presigned download URL.

### 9.4 파일 보안

- 모든 파일은 `tenantId` 격리, presigned URL 만료 ≤ 15분.
- 바이러스 스캔 (ClamAV) 후 정상만 노출.
- 개인정보 첨부는 별도 ACL (감사로그).

---

## 10. 비동기 작업 패턴

장시간 작업(일괄 import, 통계 생성, KOLIS 송신)은 202 + Job:

```
POST /api/v1/cat/bibs/bulk-import
→ 202 Accepted
   Location: /api/v1/jobs/job_01H9X
   body: { jobId, status: "QUEUED", pollUrl, eta }

GET /api/v1/jobs/{jobId}
→ { status: "RUNNING", progress: 45, resultUrl?: "..." }

GET /api/v1/jobs/{jobId}
→ { status: "SUCCEEDED", resultUrl: "/files/..." }
```

상태 코드: `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`.

선택적으로 SSE/Webhook 콜백 지원.

---

## 11. Rate Limiting · 보안 헤더

### 11.1 Rate Limit 표준

| 사용자 등급 | 한도 |
|---|---|
| 일반 사용자(OPAC) | 60 req/분/IP |
| 인증 사용자 | 300 req/분/사용자 |
| 사서 | 600 req/분/사용자 |
| 디바이스(키오스크·게이트) | 600 req/분/디바이스 |
| 서비스 간 (`/internal/*`) | 무제한 (네트워크 차단으로 보호) |
| 외부 GW 호출 | External 표준 SLA에 맞춤 |

응답:
```
429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1715404830
```

### 11.2 보안 헤더 (응답)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; ...
Cache-Control: no-store (개인정보 응답)
```

### 11.3 CORS

| 환경 | Allow-Origin |
|---|---|
| Prod | 화이트리스트 (`*.tulip.example.com`, 테넌트별 OPAC 도메인) |
| Stg | 화이트리스트 + 사내 IP |
| Dev | `*` (개발자 편의) |

---

## 12. OpenAPI 3.x 문서화

### 12.1 의무 사항

- 모든 마이크로서비스는 `springdoc-openapi` 또는 동등 도구로 OpenAPI 3.1 자동 생성 **의무**.
- 각 엔드포인트에는 `@Operation(summary, description)`, `@ApiResponse`, `@Schema` 부착.
- CI에 OpenAPI 린트(`spectral`) 통과 게이트.

### 12.2 OpenAPI 파일 규칙

```
{service-root}/openapi/v1/openapi.yaml
{service-root}/openapi/v1/components/schemas/*.yaml
```

### 12.3 메타데이터

```yaml
info:
  title: Tulip+ Circulation Service API
  version: 1.0.0
  description: 대출/반납/예약/연체 관리 API
  contact:
    name: DevLead
servers:
  - url: https://api.tulip.example.com/api/v1/cir
    description: Production
  - url: https://api-stg.tulip.example.com/api/v1/cir
    description: Staging
security:
  - bearerAuth: []
```

### 12.4 자동 검증 항목 (CI)

| 검증 | 도구 |
|---|---|
| 스키마 유효성 | spectral |
| 필수 필드·예시 | spectral 커스텀 룰 |
| Envelope 일관성 (success/code/data/meta/timestamp/traceId) | 커스텀 룰 |
| 응답 코드 정합성 (4xx/5xx envelope) | 커스텀 룰 |
| 네이밍 (kebab-case URL, camelCase JSON) | spectral |

---

## 13. 도메인별 API 표 (Phase 0 수준 — 발췌)

> Planner 각 도메인 6장 API 목록을 본 표준에 맞춰 확정. 실제 OpenAPI는 BackendSenior가 생성.

### 13.1 CIR — Circulation 핵심

| Method | Path | 인증 | Idempotency | 응답 | 비고 |
|---|---|---|---|---|---|
| POST | `/api/v1/cir/checkouts` | 사서 또는 SIP2 | **필수** | 201 + Loan | CIR-API-001 |
| POST | `/api/v1/cir/returns` | 사서/디바이스 | 필수 | 201 + ReturnReceipt | CIR-API-002 |
| POST | `/api/v1/cir/renewals` | 사서/이용자 | 필수 | 201 | CIR-API-003 |
| POST | `/api/v1/cir/holds` | 이용자 | 필수 | 201 + Hold | CIR-API-010 |
| DELETE | `/api/v1/cir/holds/{id}` | 이용자/사서 | - | 204 | CIR-API-011 |
| GET | `/api/v1/cir/members/{id}/loans` | 이용자/사서 | - | 200 + page | CIR-API-020 |
| POST | `/api/v1/cir/fines/{id}/payments` | 사서 | 필수 | 201 | CIR-API-030 |
| POST | `/api/v1/cir/ill/requests` | 이용자/사서 | 필수 | 201 | CIR-API-050 |
| POST | `/api/v1/cir/sip2` | 디바이스 토큰 | - | 200 (SIP2 응답) | CIR-API-060 (Hardware GW) |

### 13.2 CAT — Catalog 핵심

| Method | Path | 인증 | 동시성 | 응답 | 비고 |
|---|---|---|---|---|---|
| POST | `/api/v1/cat/bibs` | 사서 | - | 201 + Bib | CAT-API-001 |
| GET | `/api/v1/cat/bibs/{id}` | 사서/익명 | ETag | 200 | CAT-API-002 |
| PUT | `/api/v1/cat/bibs/{id}` | 사서 | **If-Match 필수** | 200 | CAT-API-003 |
| DELETE | `/api/v1/cat/bibs/{id}` | 사서(권한↑) | - | 204 / 409 | CAT-API-004 |
| POST | `/api/v1/cat/bibs/search` | 사서/익명 | - | 200 + cursor page | CAT-API-010 |
| POST | `/api/v1/cat/external/z3950/search` | 사서 | - | 200 + 비동기 SSE 옵션 | CAT-API-020 |
| POST | `/api/v1/cat/bibs/bulk-import` | 사서 | Idempotency | 202 + jobId | CAT-API-040 (대용량) |

### 13.3 OPAC

| Method | Path | 인증 | 캐시 | 비고 |
|---|---|---|---|---|
| GET | `/api/v1/opac/search` | 익명/이용자 | CDN 60s | CIR-060 |
| GET | `/api/v1/opac/suggest` | 익명 | CDN 5m | 자동완성 |
| GET | `/api/v1/opac/bibs/{id}` | 익명/이용자 | ETag | OPAC 상세 |
| GET | `/api/v1/opac/my/loans` | 이용자 | no-store | MyLibrary |

---

## 14. API 설계 체크리스트 (PR 게이트)

DevLead가 PR 리뷰 시 사용:

```
[ ] URL이 명사·복수형·케밥 케이스인가
[ ] 도메인 base path를 따르는가
[ ] HTTP method가 의도와 일치하는가 (생성=POST, 부분수정=PATCH)
[ ] 응답 envelope(success/code/data/meta/timestamp/traceId) 사용
[ ] 페이지네이션 표준 (offset 또는 cursor) 적용
[ ] 정렬·필터 화이트리스트 정의
[ ] 에러 코드가 04_error_codes.md 체계 준수
[ ] HTTP 상태 코드 적절 (특히 409 vs 422)
[ ] 멀티테넌트 격리 (JWT tenantId 사용, path에 tenantId 노출 금지)
[ ] 권한 어노테이션(@PreAuthorize) 부착
[ ] Idempotency-Key 필요 여부 검토
[ ] ETag/If-Match 필요 여부 검토
[ ] OpenAPI 어노테이션 부착·자동 생성 통과
[ ] Rate Limit 적용 (사용자/디바이스 등급)
[ ] 감사로그 (개인정보·정책 변경 시)
[ ] 다국어 메시지 키 사용 (`error.xxx` 형식)
```

---

## 15. 후속 산출물

| 후속 | 담당 | 시점 |
|---|---|---|
| 서비스별 OpenAPI 3.1 명세 | BackendSenior | Phase 1 착수 시 |
| API Mock 서버 (Prism) | BackendDev | Phase 1 |
| Frontend API 클라이언트 (TanStack Query + OpenAPI 코드젠) | FrontendSenior | Phase 1 |
| Postman/Newman 컬렉션 | QA | Phase 1 종료 시 |

---

## 변경 이력

| 버전 | 일자 | 변경 내용 | 작성자 |
|---|---|---|---|
| v0.1 | 2026-05-11 | Phase 0 초안 | DevLead |
