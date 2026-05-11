# Tulip+ API Gateway

> Spring Cloud Gateway (WebFlux, reactive) 기반 단일 진입점. Sprint 1-B 산출물.

## 개요

| 항목 | 값 |
|---|---|
| 모듈 | `services:api-gateway` |
| 포트 | **9100** |
| 런타임 | Java 21, Spring Boot 3.3.5, Spring Cloud 2023.0.3 |
| 책임 | 라우팅, JWT 검증, JTI 블랙리스트, 컨텍스트 헤더 전파, CORS, Rate Limit, OpenAPI 집계 |

## 핵심 흐름

```
Client ─(Bearer JWT)─▶ Gateway:9100
                         │
                         │ JwtAuthenticationFilter (order=-100)
                         │   - JWKS 캐시(1시간) 검증
                         │   - iss / aud / exp 검사
                         │   - JTI 블랙리스트 (Redis) 차단
                         │   - X-User-Id / X-Tenant-Id / X-Branch-Ids / X-Roles / X-Trace-Id 부착
                         │
                         │ TenantHeaderEnricherFilter (order=-90)
                         │   - PLATFORM_ADMIN 제외, X-Tenant-Id 누락 시 403
                         │
                         ▼
                  RequestRateLimiter (Redis, 60/min anon · 300/min user)
                         │
                         ▼
                  Route Locator → iam-service:8101 | tenant-service:8102 | …
```

## 라우팅 표 (application.yml)

| ID | Predicate | URI | 비고 |
|---|---|---|---|
| `iam-service` | `/api/v1/auth/**` | `http://localhost:8101` | Sprint 1-B 구현 완료 |
| `tenant-service` | `/api/v1/tenants/**`, `/api/v1/libraries/**`, `/api/v1/branches/**` | `http://localhost:8102` | Sprint 1-C 구현 예정 (placeholder) |
| `member-service` | `/api/v1/members/**` | `http://localhost:8103` | Sprint 1-C placeholder |
| `code-policy-service` | `/api/v1/codes/**`, `/api/v1/policies/**` | `http://localhost:8104` | Sprint 1-C placeholder |
| `keycloak-passthrough` | `/oauth2/**`, `/realms/**` | `http://localhost:8088` | Keycloak 직통 |
| `iam-openapi` | `/v3/api-docs/iam-service` | `http://localhost:8101` | SpringDoc 집계 |

## 컨텍스트 헤더 표준

| 헤더 | 출처 | 비고 |
|---|---|---|
| `X-User-Id` | JWT `sub` | 클라이언트 제공값은 폐기 |
| `X-Tenant-Id` | JWT `tenantId` | PLATFORM_ADMIN 만 임의 전환 가능 |
| `X-Branch-Ids` | JWT `branchIds` / `libraryIds` | `,` 구분 |
| `X-Roles` | JWT `roles` 또는 `realm_access.roles` | `,` 구분 |
| `X-Member-Type` | JWT `memberType` | STAFF/PATRON/DEVICE/PLATFORM_ADMIN |
| `X-Trace-Id` | W3C traceparent or 신규 UUID | 다운스트림 추적 |

## 실행 방법

### 1) 인프라 부팅 (별도 터미널)

```bash
cd /home/user/CLIPS/Tulip/backend
docker compose up -d keycloak redis postgres
```

Keycloak 은 `docker/keycloak/tulip-realm.json` 을 자동 import (`--import-realm`).

### 2) Gateway 부팅

```bash
./gradlew :services:api-gateway:bootRun
```

기동 확인:

```bash
curl http://localhost:9100/actuator/health
curl http://localhost:9100/v3/api-docs/iam-service   # 라우팅 검증
```

## 환경변수 / 설정

| Property | 기본값 | 설명 |
|---|---|---|
| `tulip.gateway.security.issuer-uri` | `http://localhost:8088/realms/tulip` | JWT iss |
| `tulip.gateway.security.jwks-uri` | `http://localhost:8088/realms/tulip/protocol/openid-connect/certs` | JWKS |
| `tulip.gateway.security.expected-audiences` | `admin-web, opac-web, iam-service, account` | aud 화이트리스트 |
| `tulip.gateway.security.public-paths` | (yml 참고) | 인증 면제 경로 |
| `spring.data.redis.host` / `.port` | `localhost / 6379` | Redis 연결 |
| `spring.cloud.gateway.globalcors.cors-configurations` | (yml 참고) | CORS 화이트리스트 |

## Rate Limit

| 대상 | 한도 | KeyResolver |
|---|---|---|
| 익명 (인증 경로 외) | 60 req/min/IP | `anonymousKeyResolver` (Forwarded-For 우선) |
| 인증 사용자 | 300 req/min/user | `userKeyResolver` (X-User-Id) |

`Redis bucket=10, replenish=5/s`. 429 응답 시 `X-RateLimit-*` 헤더 자동 부착.

## 에러 응답

모두 표준 `ApiResponse` envelope (`03_api_standards.md` §4.1) 으로 반환:

| 상황 | 코드 | HTTP |
|---|---|---|
| Authorization 누락 | `TLP-AUT-401-0001` | 401 |
| 토큰 만료 | `TLP-AUT-401-0002` | 401 |
| 서명/aud 불일치 | `TLP-AUT-401-0003` | 401 |
| JTI 블랙리스트 | `TLP-AUT-401-0003` | 401 |
| tenant 클레임 누락 | `TLP-AUT-403-0002` | 403 |

## 테스트

```bash
./gradlew :services:api-gateway:test
```

`JwtAuthenticationFilterTest` — public path, 헤더 누락(401), 정상 토큰 헤더 부착, 블랙리스트(401), 검증 실패(401), tenant 누락(403) 6 시나리오.

## TODO (다음 스프린트)

- 1-C 에서 placeholder URI 를 실제 서비스로 교체
- mTLS 인증 (디바이스용)
- Circuit Breaker 통합 (Resilience4j)
- 도메인별 OpenAPI 집계 자동화
