# Tulip+ IAM Service

> OAuth2 / OIDC BFF + Resource Server. Sprint 1-B 산출물.

## 개요

| 항목 | 값 |
|---|---|
| 모듈 | `services:iam-service` |
| 포트 | **8101** |
| 런타임 | Java 21, Spring Boot 3.3.5, Spring Security 6.3 |
| 책임 | Keycloak Authorization Code + PKCE 브로커, Refresh 회전, 로그아웃, 사용자 매핑(`iam_user_link`), JTI 블랙리스트, MFA SPI 골격, Federation SPI |

## 핵심 엔드포인트

| Method | Path | 설명 | 코드 |
|---|---|---|---|
| POST | `/api/v1/auth/login/initiate` | PKCE state/code_verifier 생성, Keycloak authorize URL 반환 | `AuthController#initiate` |
| POST | `/api/v1/auth/login/callback` | code + state 로 토큰 교환, Refresh 는 HttpOnly Cookie | `AuthController#callback` |
| POST | `/api/v1/auth/refresh` | Refresh 회전 (구 JTI 블랙리스트 적재) | `AuthController#refresh` |
| POST | `/api/v1/auth/logout` | Access/Refresh JTI 블랙리스트 + Keycloak end-session | `AuthController#logout` |
| GET  | `/api/v1/auth/me` | 현재 사용자 프로필 | `AuthController#me` |
| GET  | `/api/v1/auth/introspect` | 서비스 간 토큰 인트로스펙션 | `AuthController#introspect` |
| POST | `/api/v1/auth/mfa/setup` | MFA 등록 — 501 `TLP-AUT-MFA-501` (Phase 2 활성화) | `MfaController` |
| POST | `/api/v1/auth/mfa/verify` | MFA 검증 — 501 `TLP-AUT-MFA-501` (Phase 2 활성화) | `MfaController` |

OpenAPI: `http://localhost:8101/swagger-ui.html` / `http://localhost:8101/v3/api-docs`.

## 데이터베이스 (V1 마이그레이션)

| 테이블 | 용도 |
|---|---|
| `iam_user_link` | Keycloak `sub` ↔ 내부 `user_id` 매핑, tenant_id / default_branch_id 캐시 |
| `iam_token_blacklist` | JTI 영구 백업 (Redis 가 주 저장소) |
| `iam_refresh_audit` | Refresh 토큰 issue/rotate/revoke 감사 (보존 1년) |

스키마 적용: `./gradlew :services:iam-service:bootRun` 시 Flyway 자동 실행.

## Redis 키 스페이스

| 키 | TTL | 비고 |
|---|---|---|
| `auth:jti:blacklist:{jti}` | 토큰 만료까지 | Gateway 도 같은 키 검사 |
| `auth:pkce:state:{state}` | 5분 (`tulip.iam.pkce-ttl`) | code_verifier + redirect_uri 저장 |

## 실행 방법

### 1) 인프라 부팅

```bash
cd /home/user/CLIPS/Tulip/backend
docker compose up -d postgres redis keycloak
```

### 2) IAM 서비스 부팅

```bash
./gradlew :services:iam-service:bootRun
```

기동 확인:

```bash
curl http://localhost:8101/actuator/health
curl http://localhost:8101/v3/api-docs
```

### 3) 데모 로그인 시퀀스

전제: Keycloak realm import 완료, 데모 사용자 활성.

```bash
# 1. PKCE / state 생성
curl -X POST http://localhost:8101/api/v1/auth/login/initiate \
     -H 'Content-Type: application/json' -d '{}'
# → 응답의 authorizeUrl 을 브라우저에서 열어 librarian@demo-tenant-1 / Tulip!2026 로 로그인

# 2. Keycloak 가 http://localhost:8101/api/v1/auth/login/callback?code=...&state=... 로 리다이렉트
#    프론트엔드는 이를 그대로 콜백 엔드포인트에 POST 한다 (BFF 패턴).

# 3. /me 호출
curl http://localhost:8101/api/v1/auth/me \
     -H 'Authorization: Bearer <access_token>'

# 4. Refresh 회전 (쿠키 자동 전송)
curl -X POST http://localhost:8101/api/v1/auth/refresh -b "tulip_rt=<refresh>"

# 5. 로그아웃
curl -X POST http://localhost:8101/api/v1/auth/logout \
     -H 'Authorization: Bearer <access_token>' -b "tulip_rt=<refresh>"
```

## 환경변수 / 설정

| Property | 기본값 | 설명 |
|---|---|---|
| `tulip.iam.keycloak.issuer-uri` | `http://localhost:8088/realms/tulip` | iss |
| `tulip.iam.keycloak.token-endpoint` | `…/protocol/openid-connect/token` | 토큰 교환 |
| `tulip.iam.keycloak.end-session-endpoint` | `…/protocol/openid-connect/logout` | 로그아웃 |
| `tulip.iam.keycloak.jwks-uri` | `…/protocol/openid-connect/certs` | JWKS |
| `tulip.iam.keycloak.client-id` | `iam-service` | confidential client |
| `tulip.iam.keycloak.client-secret` | `iam-service-dev-secret` | 운영에서 KMS 주입 |
| `tulip.iam.expected-audiences` | `admin-web, opac-web, iam-service, account` | aud 화이트리스트 |
| `tulip.iam.refresh-cookie.*` | `tulip_rt / /api/v1/auth / Lax / secure=false / 12h` | HttpOnly Refresh 쿠키 |
| `spring.datasource.url` | `jdbc:postgresql://localhost:5432/tulip` | PostgreSQL |
| `spring.data.redis.host/port` | `localhost / 6379` | Redis |

## 보안 모델 요약

- Refresh Token 은 **HttpOnly Secure Cookie** 만 사용 (JS 미노출).
- Access Token 은 짧은 수명(5분) — Body 에 노출되어 클라이언트 메모리 저장.
- Refresh 회전 시 **구 JTI 를 Redis 블랙리스트에 즉시 등록** (재사용 탐지 시 전체 세션 무효).
- 로그아웃 시 Access + Refresh JTI 둘 다 블랙리스트.
- 모든 호출은 `iam_refresh_audit` 에 issue/rotate/revoke 행위 적재.

## SPI 인터페이스

### Federation (BackendDev 1-B.9)

| 인터페이스 | 위치 | 비고 |
|---|---|---|
| `FederationProvider` | `com.tulip.iam.federation.spi` | SAML/OIDC/LDAP 어댑터 구현 SPI |
| `FederationProviderRegistry` | 〃 | tenant × providerId 라우팅 |

### MFA (Phase 2 활성화)

| 인터페이스 | 위치 | 비고 |
|---|---|---|
| `TotpService` | `com.tulip.iam.mfa` | RFC 6238 TOTP — Phase 2 |

## 테스트

```bash
./gradlew :services:iam-service:test
```

- `AuthServiceTest` — initiate, callback, refresh rotation, logout, introspect
- Federation 스텁 / Registry (BackendDev 작성분 포함)

## 데모 사용자 (개발 환경)

| Username | Password | Roles | tenant_id / branch_ids |
|---|---|---|---|
| `librarian@demo-tenant-1` | `Tulip!2026` | LIBRARIAN, LIBRARIAN_CIR | `demo-tenant-1` / `[demo-tenant-1-main]` |
| `admin@demo-tenant-1` | `Tulip!2026` | LIB_ADMIN, TENANT_ADMIN, LIBRARIAN_HEAD | `demo-tenant-1` / `[main, east]` |
| `platform-admin` | `Tulip!2026` | SYS_ADMIN, PLATFORM_ADMIN | `*` (임의 전환 가능) |

## TODO (다음 스프린트)

- 1-C: `iam_user_link.tenant_id` 갱신 시 member-service Outbox 이벤트 발행
- 1-B.9: BackendDev SAML/OIDC 어댑터 구현 활성화
- 1-B.8 → Phase 2: TOTP/WebAuthn 실 구현
