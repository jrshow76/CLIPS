# Tulip+ Backend (Phase 1-A 인프라 부트스트랩)

본 디렉토리는 Tulip+ 도서관통합관리시스템의 백엔드 멀티 프로젝트 빌드 루트다.
**Phase 1-A** 는 마이크로서비스 본체를 만들기 전, 모든 서비스가 공통으로
사용하는 **6 개 common 라이브러리**와 **로컬 인프라(Docker Compose)** 만 제공한다.

서비스 모듈(`service-gateway`, `service-auth`, `service-tenant` 등)은
Phase 1-B 에서 본 라이브러리에 의존하여 추가된다.

---

## 1. 기술 스택 / 버전

| 항목 | 값 |
|---|---|
| JDK | Temurin 21 (LTS) |
| Gradle | 8.10 (`wrapper` 또는 시스템 `gradle`) |
| Spring Boot | 3.3.5 (BOM) |
| Spring Cloud | 2023.0.3 |
| MyBatis Starter | 3.0.3 |
| PostgreSQL Driver | 42.7.4 |
| jjwt | 0.12.6 |
| springdoc-openapi | 2.6.0 |
| Flyway | 10.20.0 |
| Testcontainers | 1.20.3 |

상세 매트릭스는 `gradle.properties` 를 참조한다.

---

## 2. 디렉토리 구조

```
Tulip/backend/
├── build.gradle.kts          # 루트 빌드 스크립트
├── settings.gradle           # 멀티 프로젝트 정의 (Groovy DSL)
├── gradle.properties         # 버전 매트릭스
├── buildSrc/                 # 공통 convention plugin (tulip.java-library)
├── common/
│   ├── common-core/          # ApiResponse, ErrorCode, TulipException, Pagination, Trace
│   ├── common-web/           # GlobalExceptionHandler, TraceIdFilter, OpenAPI 설정
│   ├── common-security/      # JwtTokenProvider, TulipUserPrincipal, BaseSecurityConfig
│   ├── common-tenant/        # TenantContext(Holder), TenantContextFilter, @RequiresTenant
│   ├── common-data/          # BaseDomain, AuditingInterceptor, Jsonb/Ulid TypeHandler, RLS 헬퍼
│   └── common-test/          # Testcontainers 헬퍼, TenantContextFixture
├── services/                 # (Phase 1-B 이후 서비스 모듈 추가)
├── db/migration/             # Flyway 베이스 마이그레이션
│   └── V1__init_common.sql
├── docker/                   # docker-compose 보조 파일
│   ├── postgres/initdb/
│   ├── keycloak/
│   ├── prometheus/
│   └── grafana/provisioning/datasources/
├── docker-compose.yml        # 로컬 인프라 (PG, Redis, Kafka, Keycloak, MinIO, Grafana, ...)
├── .github/workflows/
│   └── backend-ci.yml        # CI 파이프라인 (Phase 1-A placeholder 포함)
├── Makefile                  # 자주 쓰는 작업의 단축 명령
└── README.md
```

---

## 3. 빌드 / 테스트

Gradle Wrapper 가 아직 커밋되지 않았다면(`gradlew` 부재) 다음을 1회 수행한다.

```bash
gradle wrapper --gradle-version 8.10
```

> 환경에 Gradle 자체가 없으면 SDKMAN! 으로 설치하거나 (`sdk install gradle 8.10`),
> 도커로 한 번만 wrapper 를 생성 (`docker run --rm -v $PWD:/w -w /w gradle:8.10-jdk21 gradle wrapper`).

### 빌드

```bash
./gradlew build              # 전체 모듈 빌드 + 테스트
./gradlew :common:common-core:test
./gradlew assemble           # 테스트 제외 컴파일·jar
```

### 테스트

```bash
./gradlew test               # 모든 단위 테스트
./gradlew check              # test + (Phase 1-B 추가될 lint 포함)
```

---

## 4. 로컬 인프라 (Docker Compose)

```bash
make up         # 인프라 기동 (백그라운드)
make logs       # 컨테이너 로그 확인
make down       # 종료
make nuke       # 컨테이너 + 볼륨 제거
```

### 기동 후 접근

| 서비스 | URL / 포트 | 자격증명 |
|---|---|---|
| PostgreSQL | localhost:5432 | tulip / tulip / DB=tulip |
| Redis | localhost:6379 | - |
| Kafka | localhost:9092 (PLAINTEXT) | - |
| Keycloak | http://localhost:8088 | admin / admin (realm=tulip) |
| MinIO Console | http://localhost:9001 | admin / adminadmin |
| MailHog UI | http://localhost:8025 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin / admin |

---

## 5. 핵심 라이브러리 개요

### `common-core`
- `ApiResponse<T>`, `ErrorDetail`, `ResponseMeta`, `PageMeta`
- `ErrorCode` 인터페이스 + `CommonErrorCode` enum (TLP-CMN-*/TLP-SYS-*)
- `TulipException`(추상) / `BusinessException` / `ValidationException` / `NotFoundException`
- `Pagination` (offset/cursor 통합)
- `TraceContext` (W3C traceparent 발급/MDC)
- `UlidGenerator`

### `common-web`
- `GlobalExceptionHandler` (`@RestControllerAdvice`): TulipException → ApiResponse 변환
- `TraceIdFilter`, `RequestLoggingFilter`
- `OpenApiConfig` (springdoc 기본 설정)
- `CommonWebAutoConfiguration` 으로 자동 등록 (Spring Boot 3.x)

### `common-tenant`
- `TenantContext`, `TenantContextHolder`(ThreadLocal)
- `TenantContextFilter` (X-Tenant-Id 헤더 → 컨텍스트)
- `@RequiresTenant`

### `common-security`
- `JwtTokenProvider` 인터페이스 + `JjwtTokenProvider` (검증 전용)
- `TulipUserPrincipal` (sub/tenantId/libraryIds/roles/scopes 등)
- `BaseSecurityConfig` (CSRF off, Stateless, CORS, publicPaths)

### `common-data`
- `BaseDomain` + `AuditingFields`
- `AuditingInterceptor` (MyBatis Plugin — created/updated/tenantId 자동 채움)
- `JsonbTypeHandler`, `UlidTypeHandler`
- `RlsContextHelper` — `SET LOCAL app.current_tenant = ?`

### `common-test`
- `PostgresTestContainer` (재사용 가능 컨테이너)
- `TenantContextFixture` (AutoCloseable)

---

## 6. CI 워크플로 위치 안내

본 PR 단계에서는 `Tulip/backend/.github/workflows/backend-ci.yml` 에 워크플로를 두고
`paths` 필터로 backend 변경만 트리거한다.

GitHub Actions 는 기본적으로 **repository root 의 `.github/workflows`** 만 읽기 때문에,
모노레포 운영 시 다음 중 하나를 택한다.

1. (권장) repository root `.github/workflows/backend-ci.yml` 로 이동하고
   `defaults.run.working-directory: Tulip/backend` 와 `paths: ["Tulip/backend/**"]` 를 유지.
2. composite action 으로 분리 후 root workflow 에서 호출.

---

## 7. 개발 원칙 (요약)

- 모든 코드 변경은 PR 기반, DevLead 가 공통 모듈 변경을 필수 리뷰한다
  (`06_coding_standards_and_pr.md` §6.4).
- API 설계는 `03_api_standards.md`, 에러 코드는 `04_error_codes.md` 를 준수한다.
- 멀티테넌트 격리는 RLS + JWT 이중화로 강제한다 (`05_security_and_auth.md` §4).
- 복잡한 쿼리는 DBA 와 협의 후 작성한다.

---

## 8. 다음 Phase

| Phase | 산출물 |
|---|---|
| 1-A (본 PR) | common 라이브러리 6개 + 인프라 + CI placeholder |
| 1-B | service-gateway, service-auth(IAM), service-tenant 골격 |
| 1-C | service-member, service-code-policy, service-notification |
| 2~ | service-catalog, search, file 등 도메인 서비스 |
