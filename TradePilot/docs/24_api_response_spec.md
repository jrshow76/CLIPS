# TradePilot API 공통 규약 (API Response & Convention Spec)

> 문서 ID: 24_API_RESPONSE_SPEC
> 버전: v1.0
> 작성자: DevLead
> 최종 수정일: 2026-05-12
> 검토자: BackendSenior, FrontendSenior, QA, Planner

본 문서는 TradePilot의 모든 REST API가 준수해야 할 응답 포맷, 헤더, 인증, 페이지네이션, 에러 매핑, RateLimit 정책을 정의한다. 모든 백엔드/프론트엔드 개발자는 본 규약을 따라야 한다.

---

## 1. URL 규칙

### 1.1 베이스 경로
- 모든 API는 `/api/v1` 접두사를 가진다.
- 버전 업 시 `/api/v2`를 병행 운영 (Breaking Change 발생 시).

### 1.2 리소스 명명
- 리소스 명사 복수형 사용: `/orders`, `/strategies`, `/portfolios`.
- 하위 리소스: `/strategies/{id}/performance`.
- 동사/액션은 sub-path: `/orders/{id}/cancel`, `/settings/kill-switch`.
- 경로 파라미터는 snake_case 금지, `lowerCamelCase` 미사용 → **단어 그대로** (`/sectors/{code}`).

### 1.3 HTTP 메서드
| 메서드 | 의미 |
|---|---|
| GET | 조회 (멱등) |
| POST | 생성 또는 액션 |
| PATCH | 부분 수정 |
| PUT | 전체 교체 |
| DELETE | 삭제 (소프트 삭제 권장) |

---

## 2. 공통 응답 포맷

### 2.1 성공 (단일 객체)
```json
{
  "success": true,
  "data": {
    "id": "01HXYZ...",
    "name": "전략 A"
  }
}
```

### 2.2 성공 (페이지)
```json
{
  "success": true,
  "data": {
    "items": [ {...}, {...} ],
    "page": 1,
    "size": 20,
    "total": 145,
    "has_next": true
  }
}
```

### 2.3 성공 (비동기 작업 수락)
```json
{
  "success": true,
  "data": { "job_id": "01HXYZ...", "status": "QUEUED" }
}
```
- HTTP 상태: **202 Accepted**.

### 2.4 실패 (표준)
```json
{
  "success": false,
  "error": {
    "code": "E0021",
    "message": "일일 매수 한도를 초과했습니다.",
    "details": {
      "limit": 5000000,
      "attempted": 5500000
    },
    "trace_id": "8c0a2f6e-7e2b-4f15-9b1d-1f8c1a8d2e34",
    "ts": "2026-05-12T10:11:22+09:00"
  }
}
```

### 2.5 실패 (필드별 검증 오류)
```json
{
  "success": false,
  "error": {
    "code": "E0003",
    "message": "입력값을 확인해주세요.",
    "details": {
      "email": ["이메일 형식이 올바르지 않습니다."],
      "password": ["8자 이상이어야 합니다.", "특수문자를 포함해야 합니다."]
    },
    "trace_id": "...",
    "ts": "..."
  }
}
```
- HTTP 상태: **400 Bad Request**.

---

## 3. HTTP 상태 코드 매핑

| HTTP | 응답 케이스 | 비고 |
|---|---|---|
| 200 OK | 정상 조회/수정 | - |
| 201 Created | 자원 생성 성공 | `Location` 헤더 권장 |
| 202 Accepted | 비동기 작업 큐 등록 | 백테스트, ML 학습 |
| 204 No Content | 본문 없는 성공 | DELETE 등 |
| 400 Bad Request | 검증 실패 (E0003, E0055) | - |
| 401 Unauthorized | 인증 실패 (E0001, E0011) | `WWW-Authenticate: Bearer` |
| 403 Forbidden | 권한 부족 (E0002, E0013, E0016, E0092) | - |
| 404 Not Found | 자원 없음 (E0062) | - |
| 409 Conflict | 충돌 (E0006, E0017, E0022, E0028, E0051) | - |
| 410 Gone | 만료 (E0031, E0053) | - |
| 422 Unprocessable Entity | 비즈니스 검증 실패 (E0021, E0024, E0026, E0027, E0032, E0055, E0063, E0082) | - |
| 423 Locked | 계정 잠금 (E0052) | - |
| 429 Too Many Requests | RateLimit 초과 (E0008) | `Retry-After` 필수 |
| 500 Internal Server Error | 서버 오류 (E0005, E0033, E0042) | - |
| 502 Bad Gateway | 외부 시스템 오류 (E0004, E0012, E0014, E0015, E0023, E0025, E0061, E0071, E0081) | - |
| 503 Service Unavailable | 점검/의존성 단절 (E0009, E0091) | - |
| 504 Gateway Timeout | 외부 타임아웃 (E0072) | - |

> 코드 ↔ HTTP 매핑은 `14_exception_policy.md` §2.1과 일치해야 한다.

---

## 4. 인증 / 인가

### 4.1 인증 헤더
```
Authorization: Bearer <access_token>
```
- 토큰 종류: JWT (RS256 또는 HS256).
- Access: 30분, Refresh: 7일.
- 인증 실패 시 `WWW-Authenticate: Bearer realm="api"` 헤더 포함.

### 4.2 JWT Payload
```json
{
  "sub": "<user_id_uuid>",
  "role": "ROLE_TRADER_PRO",
  "trade_mode": "SIM",
  "iat": 1735000000,
  "exp": 1735001800,
  "jti": "<unique_id>"
}
```

### 4.3 권한 가드 (Role)
- `Depends(require_role("ROLE_ADMIN"))` 형태로 라우터에서 명시.
- 단일 역할이 아닌 권한 매트릭스는 `10_srs.md` §3.2를 따른다.

### 4.4 Refresh 흐름
```
POST /api/v1/auth/refresh
{ "refresh_token": "..." }
→ 200 { "access_token": "...", "expires_in": 1800 }
```
- Access 401 + `E0001` 응답 시 프론트엔드는 자동 refresh 1회 시도 후 재호출.

### 4.5 익명 허용 엔드포인트
- `/api/v1/auth/*`, `/api/v1/public/*`, `/healthz`, `/readyz`.

---

## 5. X-Trade-Mode 헤더 처리

### 5.1 적용 대상
주문/체결/포지션을 변경하는 API는 **반드시** `X-Trade-Mode` 헤더를 동반한다.

| 대상 패스 | 헤더 필수 여부 |
|---|---|
| `POST /api/v1/orders` | 필수 |
| `POST /api/v1/orders/{id}/cancel` | 필수 |
| `POST /api/v1/orders/liquidate-all` | 필수 |
| `POST /api/v1/settings/kill-switch` | 필수 |
| `POST /api/v1/settings/trade-mode/switch` | 필수 (target 값 검증) |
| 조회 API (GET) | 선택 (없으면 사용자 현재 모드 사용) |

### 5.2 값
```
X-Trade-Mode: SIM
X-Trade-Mode: LIVE
```

### 5.3 검증 규칙
1. 헤더 누락 (필수 대상) → `400 E0003` ("X-Trade-Mode 헤더가 필요합니다").
2. 값이 `SIM | LIVE`가 아님 → `400 E0003`.
3. 헤더 값과 `users.trade_mode` 불일치 → `409 E0006` (모드 재확인 모달).
4. 사용자 역할이 LIVE 비허용 (예: `ROLE_TRADER`)인데 LIVE 요청 → `403 E0002`.

### 5.4 구현 (FastAPI 미들웨어)
```python
# app/api/deps/trade_mode.py
async def require_trade_mode(
    x_trade_mode: TradeMode = Header(..., alias="X-Trade-Mode"),
    user: User = Depends(require_user),
):
    if user.trade_mode != x_trade_mode:
        raise AppException(code="E0006", http=409)
    if x_trade_mode == TradeMode.LIVE and not user.can_live():
        raise AppException(code="E0002", http=403)
    return x_trade_mode
```

---

## 6. 표준 헤더

### 6.1 요청 헤더
| 헤더 | 필수 | 설명 |
|---|---|---|
| `Authorization` | 인증 API | `Bearer <token>` |
| `Content-Type` | POST/PATCH/PUT | `application/json` |
| `X-Trade-Mode` | 주문/모드 API | `SIM \| LIVE` |
| `X-Idempotency-Key` | 주문 생성 | UUID v4 권장 |
| `X-Request-Id` | 권장 | 클라이언트 발급 trace_id |
| `Accept-Language` | 선택 | `ko`, `en` (현재 `ko`만) |

### 6.2 응답 헤더
| 헤더 | 설명 |
|---|---|
| `X-Request-Id` | 서버가 처리한 trace_id (클라이언트 발급 또는 자동) |
| `X-RateLimit-Limit` | 윈도우 한도 |
| `X-RateLimit-Remaining` | 잔여 호출 수 |
| `X-RateLimit-Reset` | 리셋 시각 (epoch sec) |
| `Retry-After` | 429/503 시 재시도 권장 시간 (sec) |
| `Cache-Control` | 캐시 정책 (예: `no-store`, `max-age=3`) |

---

## 7. 페이지네이션 / 정렬 / 필터

### 7.1 쿼리 파라미터
| 파라미터 | 기본 | 최대 | 설명 |
|---|---|---|---|
| `page` | 1 | - | 1-based |
| `size` | 20 | 100 | 페이지 크기 |
| `sort` | 엔드포인트별 기본 | - | `field,asc|desc` 콤마 구분 |

### 7.2 다중 정렬
```
GET /api/v1/recommendations?sort=score,desc&sort=volume,desc
```
- 정렬 가능 필드는 엔드포인트별로 화이트리스트.

### 7.3 필터 표기
| 패턴 | 예시 |
|---|---|
| 단순 비교 | `status=ACTIVE` |
| 범위 | `from=2026-01-01&to=2026-05-12` |
| 다중 선택 | `sector=IT&sector=BIO` (반복) |
| 부분 일치 | `q=삼성` (검색용) |

### 7.4 응답 메타
```json
{
  "items": [...],
  "page": 1,
  "size": 20,
  "total": 145,
  "has_next": true
}
```
- 총 카운트가 비용이 큰 경우 `total: null`을 허용하고 `has_next`만 신뢰한다.

---

## 8. 멱등성 (Idempotency)

### 8.1 적용 대상
- 모든 **자원 변경 POST** (특히 `POST /api/v1/orders`).

### 8.2 정책
- 헤더: `X-Idempotency-Key: <uuid>`.
- 서버는 24시간 동안 (key, user_id, endpoint) 조합으로 결과를 캐시.
- 동일 키 재요청 시 기존 응답 (HTTP status 포함) 반환.
- 키 누락 시: 동일 사용자 + 종목 + side + qty + 60초 윈도우 기준으로 중복 차단 (E0022).

### 8.3 저장 위치
- Redis: `idem:{user_id}:{endpoint}:{key}` → 응답 직렬화, TTL 24h.

---

## 9. 날짜 / 시간 / 숫자 / 통화

### 9.1 시간대
- 모든 timestamp는 ISO-8601 + 오프셋: `2026-05-12T10:11:22+09:00`.
- 시계열 응답에서 대용량은 epoch milliseconds (UTC) 사용: `"ts": 1736700000000`.
- 입력은 ISO-8601 또는 `YYYY-MM-DD`.

### 9.2 숫자
- 정수: `int64` 범위.
- 가격/금액: `decimal` (서버 내부) → JSON에서는 `number` (정수 원, 소수점 없음).
- 비율(퍼센트): `float`, 단위는 % (예: `5.0`이 5%).

### 9.3 통화
- `currency` 필드 명시: 기본 `KRW`.
- 외화 미사용 (v1.0 KRW only).

### 9.4 종목코드 / 표현
- 6자리 숫자 문자열: `"005930"` (선행 0 유지).
- 종목명은 항상 한글 우선, 영문 별칭은 별도 필드.

---

## 10. 에러 코드 매핑 (요약)

> 상세는 `14_exception_policy.md` §2 참조.

### 10.1 그룹
| 그룹 | 코드 범위 | 도메인 |
|---|---|---|
| 00 | E0001~E0009 | 공통/시스템 |
| 01 | E0011~E0019 | 인증/모드 전환 |
| 02 | E0021~E0029 | 주문/매매 |
| 03 | E0031~E0039 | 백테스트 |
| 04 | E0041~E0049 | ML |
| 05 | E0051~E0059 | 사용자/계정 |
| 06 | E0061~E0069 | 시세/시장 데이터 |
| 07 | E0071~E0079 | 외부 시스템 |
| 08 | E0081~E0089 | 알림 |
| 09 | E0091~E0099 | 운영 |

### 10.2 응답 매핑 원칙
- HTTP 상태와 에러 코드는 1:N 관계 (HTTP 1개에 여러 에러 코드 가능).
- 사용자 메시지는 `14_exception_policy.md` §10 톤 가이드 준수.
- `details`에 기술 세부를 담되, 스택 트레이스/내부 경로는 금지.

### 10.3 게이트웨이 에러 매핑
- creon-gateway의 `G0xxx` 코드는 본체에서 `Exxxx`로 변환 (`23_creon_gateway.md` §5.4).
- 응답 시에는 항상 `Exxxx`만 노출.

---

## 11. RateLimit

### 11.1 정책
| 구간 | 윈도우 | 한도 |
|---|---|---|
| 인증 API (`/auth/*`) | 1분 | 10회/IP |
| 시세/지표 조회 | 1초 | 10회/사용자 |
| 주문 생성 | 1초 | 3회/사용자, 1일 1,000건 |
| 일반 조회 | 1분 | 600회/사용자 |
| 관리자 API | 1분 | 60회/사용자 |

### 11.2 구현
- Redis 기반 슬라이딩 윈도우 카운터.
- 미들웨어에서 검사, 초과 시 `429 E0008` + `Retry-After`.

### 11.3 응답 헤더 예시
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1736700090
Retry-After: 12
```

---

## 12. CORS

- 허용 Origin: `NEXT_PUBLIC_APP_URL` 환경변수 + 운영 도메인.
- 허용 메서드: `GET, POST, PATCH, PUT, DELETE, OPTIONS`.
- 허용 헤더: `Authorization, Content-Type, X-Trade-Mode, X-Idempotency-Key, X-Request-Id`.
- 노출 헤더: `X-Request-Id, X-RateLimit-*, Retry-After`.

---

## 13. WebSocket 규약

### 13.1 채널
| Path | 용도 |
|---|---|
| `/ws/quotes` | 시세 push |
| `/ws/signals` | 시그널/주문 업데이트 |
| `/ws/notifications` | 인앱 알림 |

### 13.2 인증
- 쿼리 파라미터 `?token=<access_token>` 또는 첫 메시지로 인증.
- 인증 실패 시 close code `4401`.

### 13.3 메시지 포맷
```json
// 클라이언트 → 서버 (구독)
{ "type": "subscribe", "codes": ["005930", "000660"] }

// 서버 → 클라이언트 (이벤트)
{ "type": "quote", "code": "005930", "price": 71200, "ts": 1736700090000 }
{ "type": "signal", "id": "...", "code": "...", "action": "BUY", ... }
{ "type": "order_update", "id": "...", "status": "FILLED", "filled_qty": 10 }
{ "type": "notification", "id": "...", "title": "...", "body": "..." }
```

### 13.4 Close Codes
| 코드 | 의미 |
|---|---|
| 1000 | 정상 종료 |
| 4401 | 인증 실패 |
| 4429 | RateLimit |
| 4503 | 서버 점검 |

---

## 14. 버저닝 / 호환성

- Breaking Change 발생 시 `/api/v2` 신설, `/api/v1`은 최소 6개월 병행.
- 필드 추가는 Non-Breaking (기존 클라이언트가 무시).
- 필드 삭제/타입 변경/필수화는 Breaking.
- OpenAPI 스펙은 `/api/v1/openapi.json` 자동 공개 (운영은 인증 필요).

---

## 15. API 문서화

- FastAPI 자동 OpenAPI + Swagger UI: `/docs` (개발 환경만), `/redoc`.
- 운영 환경은 인증 후 열람.
- 각 엔드포인트 함수에 `summary`, `description`, `response_model` 필수.

---

## 16. 보안 추가 사항

| 항목 | 정책 |
|---|---|
| HTTPS | 운영 환경 강제, nginx HSTS 헤더 포함 |
| CSRF | JWT + SameSite Cookie 정책으로 회피 (BFF 없는 구조) |
| XSS | 응답은 항상 JSON, 사용자 입력은 escape |
| Audit | 모든 변경 API는 `audit_log` 기록 (`14_exception_policy.md` §9.2) |

---

## 17. 응답 예시 모음

### 17.1 주문 생성 (성공)
```
POST /api/v1/orders
Authorization: Bearer ...
X-Trade-Mode: LIVE
X-Idempotency-Key: 5f1c8a8e-...
Content-Type: application/json

{ "code": "005930", "side": "BUY", "qty": 10, "order_type": "MARKET" }
```
```
HTTP/1.1 201 Created
Content-Type: application/json
X-Request-Id: 5f1c8a8e-...

{
  "success": true,
  "data": {
    "id": "01HXYZ...",
    "code": "005930",
    "side": "BUY",
    "qty": 10,
    "order_type": "MARKET",
    "status": "ACCEPTED",
    "mode": "LIVE",
    "broker_order_no": "12345678",
    "created_at": "2026-05-12T10:11:22+09:00"
  }
}
```

### 17.2 주문 한도 초과 (실패)
```
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "success": false,
  "error": {
    "code": "E0021",
    "message": "일일 매수 한도를 초과했습니다.",
    "details": { "limit": 5000000, "attempted": 5500000 },
    "trace_id": "...",
    "ts": "2026-05-12T10:11:22+09:00"
  }
}
```

### 17.3 모드 불일치 (실패)
```
HTTP/1.1 409 Conflict
X-Request-Id: ...

{
  "success": false,
  "error": {
    "code": "E0006",
    "message": "매매 모드가 일치하지 않습니다.",
    "details": { "header_mode": "LIVE", "user_mode": "SIM" }
  }
}
```

---

## 18. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | DevLead | 최초 작성 |
