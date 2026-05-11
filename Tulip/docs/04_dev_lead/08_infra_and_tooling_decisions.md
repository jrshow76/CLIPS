# 인프라·기술 결정서 (Infrastructure & Tooling Decisions)

| 항목 | 내용 |
|---|---|
| 문서명 | Tulip+ 인프라·기술 스택 결정서 |
| 문서 ID | DEV-08 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | DevLead Agent |
| 검토자 | PM, BackendSenior, FrontendSenior, DBA, QA |
| 입력 | `01_architecture_overview.md`, `02_service_decomposition.md`, `06_coding_standards_and_pr.md`, `10_dba/01_data_modeling_principles.md` |
| 후속 | `07_phase1_sprint_plan.md`, 서비스별 코드 템플릿 |
| 상태 | Phase 0 초안, Phase 1 진입 직전 Baseline 동결 예정 |

---

## 1. 문서 목적

본 문서는 Tulip+ 도서관통합관리시스템의 **인프라 컴포넌트·언어·프레임워크·도구·버전**에 대한 결정을 명시하고, 각 결정의 **근거와 대안 비교**를 기록한다. BackendSenior·FrontendSenior·DBA가 본 문서를 즉시 코드/IaC로 옮길 수 있는 수준의 구체성을 가진다.

결정 원칙:
1. **LTS 우선**: 모든 핵심 컴포넌트는 LTS 또는 안정 마이너 라인 사용
2. **표준 우선**: 의심스러우면 Spring/PostgreSQL/Next.js 표준 채택, 사설 도구 회피
3. **명시적 버전 고정**: BOM·workspace에서 단일 버전 정의, 서비스별 변동 금지
4. **로컬-Stg-Prod 일관성**: 동일 컨테이너 이미지·동일 마이그레이션 도구

---

## 2. 백엔드 모노레포 구조

### 2.1 결정: Gradle Multi-Project (Kotlin DSL)

| 대안 | 평가 |
|---|---|
| Gradle Multi-Project + Kotlin DSL | **채택** — 의존성 관리 강력, BOM·convention plugin 활용, IDE 통합 우수 |
| Maven Multi-Module | 미채택 — XML 장황, 빌드 캐시 약함 |
| Bazel | 미채택 — 학습 곡선 가파름, Spring/Java 생태계 친화성 낮음 |
| Repo 분리 (서비스별) | 미채택 — 공통 라이브러리 변경 시 N개 PR, 일관성 유지 비용↑ |

### 2.2 디렉토리 구조

```
tulip-backend/
├── settings.gradle.kts            # 모든 서브프로젝트 include
├── build.gradle.kts               # 공통 설정 (Java toolchain, repositories)
├── gradle.properties              # org.gradle.jvmargs, JIT, parallel
├── gradle/libs.versions.toml      # 버전 카탈로그 (Version Catalog)
├── buildSrc/                      # 컨벤션 플러그인
│   └── src/main/kotlin/
│       ├── tulip.java-conventions.gradle.kts
│       ├── tulip.spring-conventions.gradle.kts
│       ├── tulip.test-conventions.gradle.kts
│       └── tulip.docker-conventions.gradle.kts
├── platform/
│   ├── tulip-bom/                 # 의존성 BOM (java-platform plugin)
│   │   └── build.gradle.kts
│   └── tulip-common/
│       ├── tulip-common-core/         # ErrorCode, ApiResponse, Trace, MDC
│       ├── tulip-common-web/          # Filter, Interceptor, ExceptionHandler
│       ├── tulip-common-security/     # JWT, TenantContext, RBAC, OAuth2 Resource Server
│       ├── tulip-common-data/         # MyBatis 설정, RLS Interceptor, Crypto TypeHandler
│       ├── tulip-common-tenant/       # TenantResolver, TenantContextHolder, MultiTenant ThreadLocal/Reactor Context
│       └── tulip-common-event/        # Outbox, Kafka Producer/Consumer Helper
├── services/
│   ├── iam-service/
│   ├── tenant-service/
│   ├── member-service/
│   ├── code-policy-service/
│   ├── catalog-service/
│   ├── collection-service/
│   ├── acquisition-service/
│   ├── circulation-service/
│   ├── access-service/
│   ├── facility-service/
│   ├── search-service/
│   ├── stats-report-service/
│   ├── notification-service/
│   ├── file-service/
│   ├── external-gateway/
│   └── hardware-gateway/
├── bff/
│   ├── admin-bff/
│   └── opac-bff/
└── infra/
    ├── api-gateway/                   # Spring Cloud Gateway
    ├── batch/                         # Spring Batch (연체·통계·이월)
    └── compose/                       # Docker Compose 정의 (로컬·Dev)
```

### 2.3 settings.gradle.kts 핵심

```kotlin
rootProject.name = "tulip-backend"

pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositories {
        mavenCentral()
        maven { url = uri("https://repo.spring.io/milestone") }
    }
}

// platform
include(":platform:tulip-bom")
listOf("core", "web", "security", "data", "tenant", "event").forEach {
    include(":platform:tulip-common:tulip-common-$it")
}

// services
listOf(
    "iam", "tenant", "member", "code-policy",
    "catalog", "collection", "acquisition", "circulation",
    "access", "facility", "search", "stats-report",
    "notification", "file", "external-gateway", "hardware-gateway"
).forEach { include(":services:$it-service") }

// bff
include(":bff:admin-bff", ":bff:opac-bff")

// infra
include(":infra:api-gateway", ":infra:batch")
```

### 2.4 tulip-common 모듈별 책임

| 모듈 | 책임 | 의존 |
|---|---|---|
| `tulip-common-core` | `ErrorCode`, `ApiResponse<T>`, `PageRequest`, `PageResponse`, `TraceId`, MDC 키 상수 | (없음) |
| `tulip-common-web` | `GlobalExceptionHandler`, `RequestLoggingFilter`, `IdempotencyFilter`, OpenAPI 공통 설정 | core |
| `tulip-common-security` | JWT 발급/검증, `@CurrentUser`, `@PreAuthorize` Voter, Method Security 설정 | core, web |
| `tulip-common-data` | MyBatis Auto-config, RLS Interceptor(tenant_id 누락 차단), pgcrypto TypeHandler, Soft Delete Interceptor | core |
| `tulip-common-tenant` | `TenantContextHolder`(ThreadLocal + Reactor Context), `TenantContextFilter`, JDBC 커넥션에 `SET app.tenant_id` 주입 | core, web, data |
| `tulip-common-event` | Outbox Entity/Mapper, Polling Publisher, Kafka 공통 Producer/Consumer, 이벤트 envelope | core, data |

---

## 3. 핵심 버전 매트릭스

### 3.1 백엔드

| 컴포넌트 | 버전 | 근거 |
|---|---|---|
| **Java** | **21 LTS** | 2026-05 기준 최신 LTS. Virtual Thread(Project Loom)로 SIP2/외부 호출 동시성 이점. 차기 LTS Java 25(2025-09)는 안정성 확보 후 Phase 4 검토 |
| **Spring Boot** | **3.3.x** (Latest 3.3 LTS) | Java 21 지원, Native 옵션, Spring Framework 6.1. 3.4는 마이너 안정화 후 채택 검토 |
| **Spring Cloud** | **2023.0.x** (Leyton) | Spring Boot 3.3 호환 트레인. Gateway·OpenFeign·Resilience4j 안정판 |
| **Spring Security** | 6.3 (Boot 3.3 동봉) | OAuth2 Resource Server + Authorization Server 분리 정책 |
| **Spring Cloud Gateway** | 4.1.x | Reactive Gateway, JWT Predicate, Rate Limit |
| **Spring Batch** | 5.1.x | Job 등록 기반, Java DSL |
| **MyBatis** | 3.5.x | (Phase 0 결정 — DEV-06 `2.8`) |
| **MyBatis Spring** | **3.0.x** | Spring Boot 3 호환 라인 |
| **mybatis-spring-boot-starter** | 3.0.x | Auto-config |
| **PostgreSQL JDBC** | 42.7.x | PG 15+ 호환 |
| **HikariCP** | 5.x (Boot 동봉) | 커넥션 풀 표준 |
| **Lombok** | 1.18.x | 코딩 규약(DEV-06 2.7) 준수 |
| **MapStruct** | 1.6.x | DTO ↔ Domain 매핑 |
| **Jackson** | 2.17.x (Boot 동봉) | JSON 직렬화, JSONB 지원 |
| **Resilience4j** | 2.2.x | 서킷 브레이커·재시도·벌크헤드 (External GW) |
| **Micrometer** | 1.13.x | Prometheus + Tempo Trace |
| **OpenTelemetry Java Agent** | 2.x | APM·분산 추적 |
| **springdoc-openapi** | 2.6.x | OpenAPI 3.1 문서 |
| **Testcontainers** | 1.20.x | PG/Kafka/Redis 통합 테스트 |
| **JUnit Jupiter** | 5.10.x | 단위 테스트 |
| **AssertJ** | 3.26.x | 도메인 어설션 |
| **Mockito** | 5.x | Mock |
| **WireMock** | 3.x | 외부 API mocking |
| **Flyway** | **10.x** | DB 마이그레이션 |
| **Gradle** | **8.10+** | Build |
| **Kotlin DSL** | 2.0 (build script) | 타입 안전한 빌드 스크립트 |

### 3.2 프론트엔드

| 컴포넌트 | 버전 | 근거 |
|---|---|---|
| **Node.js** | **20 LTS** | 2026 안정 LTS. Next.js 15 권장 |
| **pnpm** | **9.x** | workspace 표준, 디스크 효율 |
| **Turborepo** | **2.x** | 빌드 캐시·incremental |
| **TypeScript** | **5.5+** | strict, satisfies, const generic |
| **Next.js** | **15 (App Router)** | React 19 RC + Turbopack stable + Server Actions |
| **React** | 19 | Next.js 15 동봉 |
| **Tailwind CSS** | **4.x** | Lightning CSS 기반, Oxide 엔진 |
| **shadcn/ui** | latest | 기반 컴포넌트 라이브러리 (Radix UI 기반) |
| **Radix UI** | 1.x (shadcn 의존) | 접근성 primitives |
| **TanStack Query** | **5.x** | 서버 상태 |
| **Zustand** | 5.x | 클라이언트 전역 상태 |
| **Zod** | 3.23.x | 스키마 검증 |
| **React Hook Form** | 7.x | 폼 |
| **nuqs** | 2.x | URL 상태 |
| **next-intl** | 3.x | 다국어 |
| **Playwright** | 1.46.x | E2E |
| **Vitest** | 2.x | 단위 |
| **Testing Library (React)** | 16.x | 컴포넌트 |
| **Storybook** | 8.x | 컴포넌트 카탈로그 |
| **ESLint** | 9.x (Flat config) | 린트 |
| **Prettier** | 3.x | 포맷 |

### 3.3 결정 근거 요약

- **Java 21 + Boot 3.3**: PM 헌장(`5.4` 기술 스택)과 정합. Virtual Thread로 외부 표준 연동(KOLIS/Z39.50/SIP2)에서 스레드풀 고갈 없이 동시성 처리.
- **Next.js 15 + React 19**: App Router 안정화 완료, Server Action으로 BFF 일부 대체 가능, SEO·SSR 핵심인 OPAC에 유리.
- **Tailwind 4**: Tailwind 3 대비 빌드 속도 대폭 개선. Designer 디자인 토큰을 `@theme`로 직접 매핑 가능.
- **Gradle 8.x + Kotlin DSL + Version Catalog**: 단일 진실원(`libs.versions.toml`)으로 BOM과 함께 이중 안전망.

---

## 4. 로컬 인프라 — Docker Compose

### 4.1 컴포넌트 카탈로그

| 컴포넌트 | 이미지 | 버전 | 포트 | 용도 |
|---|---|---|---|---|
| PostgreSQL | `postgres:15.7-alpine` | **15.7** | 5432 | 메인 DB. `pgcrypto`, `pg_trgm`, `unaccent`, `btree_gin`, `pgaudit`, `pg_stat_statements` 활성 |
| Redis | `redis:7.4-alpine` | 7.4 | 6379 | 세션·Rate Limit·JTI 블랙리스트·캐시 |
| Kafka | `bitnami/kafka:3.7` | 3.7 | 9092 | 이벤트 버스 (Phase 1은 Zookeeper 모드, Phase 2 KRaft 검토) |
| Zookeeper | `bitnami/zookeeper:3.9` | 3.9 | 2181 | Kafka 메타데이터 (Phase 1 한정) |
| Keycloak | `quay.io/keycloak/keycloak:24.0` | **24.0** | 8080 | OAuth2/OIDC IdP, SSO Federation |
| MinIO | `minio/minio:RELEASE.2024-08-17` | latest | 9000/9001 | S3 호환 파일 스토리지 |
| Mailhog | `mailhog/mailhog:v1.0.1` | 1.0 | 1025/8025 | 메일 송신 테스트 |
| Prometheus | `prom/prometheus:v2.54` | 2.54 | 9090 | 메트릭 수집 |
| Grafana | `grafana/grafana:11.2` | 11.2 | 3001 | 대시보드 |
| Loki | `grafana/loki:3.1` | 3.1 | 3100 | 로그 집계 |
| Tempo | `grafana/tempo:2.5` | 2.5 | 3200 | 분산 추적 |
| OTel Collector | `otel/opentelemetry-collector:0.106` | 0.106 | 4317/4318 | 추적·메트릭·로그 게이트웨이 |
| OpenSearch | `opensearchproject/opensearch:2.15` | 2.15 | 9200 | OPAC 서지 검색 (Phase 2 본격 사용, Phase 1은 컨테이너만 띄움) |
| OpenSearch Dashboards | `opensearchproject/opensearch-dashboards:2.15` | 2.15 | 5601 | OS 관리 |

> **OpenSearch vs Elasticsearch**: OpenSearch 채택. 라이센스(Apache 2.0) + AWS 친화 + 한국어 분석기(nori) 정식 지원. Elasticsearch 8 SSPL은 SaaS 제공 시 라이센스 리스크.

### 4.2 docker-compose.yml 골격

```yaml
version: "3.9"

x-common-env: &common-env
  TZ: Asia/Seoul

services:
  postgres:
    image: postgres:15.7-alpine
    environment:
      <<: *common-env
      POSTGRES_USER: tulip
      POSTGRES_PASSWORD: tulip_local
      POSTGRES_DB: tulip
    command:
      - "postgres"
      - "-c"
      - "shared_preload_libraries=pg_stat_statements,pgaudit"
      - "-c"
      - "log_statement=mod"
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init/postgres:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tulip"]
      interval: 5s
      retries: 12

  redis:
    image: redis:7.4-alpine
    command: ["redis-server", "--appendonly", "yes"]
    ports: ["6379:6379"]
    volumes: ["redisdata:/data"]

  zookeeper:
    image: bitnami/zookeeper:3.9
    environment:
      ALLOW_ANONYMOUS_LOGIN: "yes"
    ports: ["2181:2181"]

  kafka:
    image: bitnami/kafka:3.7
    depends_on: [zookeeper]
    environment:
      KAFKA_CFG_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_CFG_LISTENERS: PLAINTEXT://:9092
      KAFKA_CFG_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      ALLOW_PLAINTEXT_LISTENER: "yes"
      KAFKA_CFG_AUTO_CREATE_TOPICS_ENABLE: "false"
    ports: ["9092:9092"]

  keycloak:
    image: quay.io/keycloak/keycloak:24.0
    command: ["start-dev", "--import-realm"]
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin_local
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: tulip
      KC_DB_PASSWORD: tulip_local
    depends_on:
      postgres:
        condition: service_healthy
    ports: ["8080:8080"]
    volumes:
      - ./keycloak/realm-export.json:/opt/keycloak/data/import/realm.json:ro

  minio:
    image: minio/minio:RELEASE.2024-08-17T01-24-54Z
    command: ["server", "/data", "--console-address", ":9001"]
    environment:
      MINIO_ROOT_USER: tulip
      MINIO_ROOT_PASSWORD: tulip_local_minio
    ports: ["9000:9000", "9001:9001"]
    volumes: ["miniodata:/data"]

  mailhog:
    image: mailhog/mailhog:v1.0.1
    ports: ["1025:1025", "8025:8025"]

  prometheus:
    image: prom/prometheus:v2.54.1
    volumes: ["./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro"]
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:11.2.0
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin_local
    ports: ["3001:3000"]
    volumes:
      - grafanadata:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro

  loki:
    image: grafana/loki:3.1.0
    command: ["-config.file=/etc/loki/local-config.yaml"]
    ports: ["3100:3100"]

  tempo:
    image: grafana/tempo:2.5.0
    command: ["-config.file=/etc/tempo.yaml"]
    volumes: ["./tempo/tempo.yaml:/etc/tempo.yaml:ro"]
    ports: ["3200:3200", "4317:4317", "4318:4318"]

  opensearch:
    image: opensearchproject/opensearch:2.15.0
    environment:
      discovery.type: single-node
      DISABLE_SECURITY_PLUGIN: "true"
      OPENSEARCH_JAVA_OPTS: "-Xms512m -Xmx512m"
    ports: ["9200:9200"]
    volumes: ["osdata:/usr/share/opensearch/data"]

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:2.15.0
    environment:
      DISABLE_SECURITY_DASHBOARDS_PLUGIN: "true"
      OPENSEARCH_HOSTS: '["http://opensearch:9200"]'
    ports: ["5601:5601"]

volumes:
  pgdata:
  redisdata:
  miniodata:
  grafanadata:
  osdata:
```

### 4.3 init/postgres/01-extensions.sql

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pgaudit;

-- DB 분리: 서비스별 데이터베이스
CREATE DATABASE keycloak;
CREATE DATABASE tulip_iam;
CREATE DATABASE tulip_tenant;
CREATE DATABASE tulip_member;
CREATE DATABASE tulip_code_policy;
-- (이후 도메인 DB는 Phase 2~5에서 추가)

-- 또는: 단일 DB + 스키마 분리 (Phase 1 채택)
\c tulip
CREATE SCHEMA iam;
CREATE SCHEMA tenant;
CREATE SCHEMA member;
CREATE SCHEMA code_policy;
CREATE SCHEMA notification;
CREATE SCHEMA file;
```

> **DB 분리 vs 스키마 분리**: Phase 1은 **단일 DB + 스키마 분리** 채택. 운영 확장 시(테넌트 1,000개 도달) 도메인별 DB 분리로 마이그레이션 옵션 유지. 결정 근거는 DBA `01_data_modeling_principles.md` §2와 정합.

---

## 5. 프론트엔드 모노레포

### 5.1 결정: pnpm Workspace + Turborepo

| 대안 | 평가 |
|---|---|
| pnpm + Turborepo | **채택** — 디스크 효율, remote cache, Vercel 친화 |
| npm workspaces | 미채택 — symlink 이슈, hoisting 충돌 |
| Yarn Berry (PnP) | 미채택 — 호환성 이슈, 학습 곡선 |
| Nx | 미채택 — Turborepo 대비 무거움. 단, 그래프 시각화는 차후 검토 |

### 5.2 디렉토리 구조

```
tulip-frontend/
├── package.json                   # workspace 루트
├── pnpm-workspace.yaml
├── turbo.json
├── tsconfig.base.json
├── .npmrc                         # public-hoist-pattern[], strict-peer-dependencies=true
├── apps/
│   ├── admin/                     # 사서 관리자 (Next.js 15)
│   │   ├── next.config.mjs
│   │   ├── tailwind.config.ts
│   │   ├── package.json
│   │   └── src/
│   │       ├── app/               # App Router
│   │       ├── features/
│   │       ├── shared/
│   │       └── widgets/
│   └── opac/                      # OPAC (Next.js 15)
│       └── ...
├── packages/
│   ├── design-tokens/             # Designer 산출물 (색·타이포·spacing) + Tailwind plugin
│   │   ├── src/
│   │   │   ├── colors.ts
│   │   │   ├── typography.ts
│   │   │   ├── spacing.ts
│   │   │   ├── radii.ts
│   │   │   └── tailwind-preset.ts
│   │   └── package.json
│   ├── ui/                        # 공통 컴포넌트 라이브러리 (shadcn 기반)
│   │   ├── src/components/
│   │   ├── .storybook/
│   │   └── package.json
│   ├── api-client/                # OpenAPI → TypeScript 자동 생성
│   │   ├── src/
│   │   │   ├── generated/         # codegen 결과
│   │   │   ├── queries/           # TanStack Query hooks
│   │   │   └── index.ts
│   │   └── openapi-codegen.config.ts
│   ├── auth/                      # 인증 hooks/context, JWT 핸들링
│   │   └── src/
│   ├── config/                    # 환경변수·설정 공통화 (zod 검증)
│   │   └── src/
│   ├── i18n/                      # 다국어 메시지 사전
│   │   └── src/locales/
│   ├── icons/                     # 아이콘 컴포넌트
│   └── eslint-config/             # 공통 ESLint config (flat)
└── scripts/
    ├── codegen.ts                 # OpenAPI 코드 생성
    └── lint-all.ts
```

### 5.3 패키지 명명 (Scoped)

| 패키지 | 이름 |
|---|---|
| 디자인 토큰 | `@tulip/design-tokens` |
| UI 컴포넌트 | `@tulip/ui` |
| API 클라이언트 | `@tulip/api-client` |
| 인증 | `@tulip/auth` |
| 설정 | `@tulip/config` |
| 다국어 | `@tulip/i18n` |
| 아이콘 | `@tulip/icons` |
| ESLint 공통 | `@tulip/eslint-config` |
| 관리자 앱 | `@tulip/admin` (private) |
| OPAC 앱 | `@tulip/opac` (private) |

### 5.4 pnpm-workspace.yaml

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

### 5.5 turbo.json

```json
{
  "$schema": "https://turbo.build/schema.json",
  "ui": "tui",
  "globalDependencies": [".env", ".env.local"],
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "!.next/cache/**", "dist/**"]
    },
    "lint": { "dependsOn": ["^lint"] },
    "test": { "dependsOn": ["^build"], "outputs": ["coverage/**"] },
    "test:e2e": { "dependsOn": ["build"] },
    "type-check": { "dependsOn": ["^build"] },
    "codegen": { "outputs": ["packages/api-client/src/generated/**"] },
    "dev": { "cache": false, "persistent": true }
  }
}
```

### 5.6 OpenAPI codegen 전략

| 도구 | 평가 |
|---|---|
| **`@hey-api/openapi-ts`** | **채택** — TS 우선, TanStack Query 어댑터, tree-shakable |
| `openapi-typescript-codegen` | 차순위 — 안정적, 단 유지보수 둔화 |
| `orval` | 검토 — TanStack Query 통합 우수, 단 빌드 시간 길음 |

스크립트:
```bash
# tulip-frontend/scripts/codegen.ts
# 16개 서비스 OpenAPI YAML 수집 → packages/api-client/src/generated/<service>/ 생성
```

CI 파이프라인에서 백엔드 OpenAPI 변경 시 자동 PR 생성 (Renovate-like).

---

## 6. DB 마이그레이션 — Flyway

### 6.1 결정: Flyway 10.x

| 대안 | 평가 |
|---|---|
| Flyway | **채택** — SQL 우선, 단순, Spring Boot 통합 |
| Liquibase | 미채택 — XML/YAML 추상화 과다, 팀 학습 비용 |

### 6.2 서비스별 마이그레이션 디렉토리

```
services/<service>/src/main/resources/db/migration/
├── V1__init.sql                                  # 베이스라인
├── V20260711_001__create_member_table.sql        # 날짜+일련번호
├── V20260712_001__add_member_consent.sql
├── R__refresh_member_view.sql                    # Repeatable
└── ...
```

### 6.3 네이밍 컨벤션

| 종류 | 패턴 |
|---|---|
| Versioned (변경 불가) | `V{YYYYMMDD}_{NNN}__<snake_case_description>.sql` |
| Repeatable (재실행 가능) | `R__<snake_case_description>.sql` |
| Undo (Enterprise) | 미사용 (OSS 버전) |

### 6.4 V1__init.sql 구조

```sql
-- =============================================================
-- Tulip+ Phase 1 Baseline
-- Service: <service-name>
-- Date: 2026-07-XX
-- =============================================================

-- 1) Schema 보장
CREATE SCHEMA IF NOT EXISTS <service_schema>;
SET search_path TO <service_schema>;

-- 2) RLS 헬퍼 함수 (common, 모든 서비스에서 동일)
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS BIGINT AS $$
  SELECT NULLIF(current_setting('app.tenant_id', true), '')::BIGINT;
$$ LANGUAGE SQL STABLE;

-- 3) updated_at 트리거 함수 (common)
CREATE OR REPLACE FUNCTION fn_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  NEW.version := COALESCE(OLD.version, 0) + 1;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4) 도메인 테이블 (예: tenant)
CREATE TABLE tlp_cmn_tenant (
  id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  tenant_id   BIGINT NOT NULL,    -- 자기참조
  code        VARCHAR(32) NOT NULL,
  name        VARCHAR(200) NOT NULL,
  status      VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by  BIGINT,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by  BIGINT,
  deleted_at  TIMESTAMPTZ,
  version     INT NOT NULL DEFAULT 0,
  CONSTRAINT uk_tenant_code UNIQUE (code)
);

CREATE TRIGGER trg_tenant_biu_audit
  BEFORE UPDATE ON tlp_cmn_tenant
  FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- 5) RLS 활성화 (메타 테이블은 platform admin만 접근하므로 정책 없음 또는 슈퍼관리자 BYPASS)
ALTER TABLE tlp_cmn_tenant ENABLE ROW LEVEL SECURITY;
-- 정책은 다른 도메인 테이블에 적용
```

### 6.5 운영 정책

- 모든 DDL은 **DBA 승인** (DEV-06 §4.2).
- Versioned 마이그레이션은 **수정 절대 금지**.
- 컬럼 추가는 3단계 무중단 (Nullable → 백필 → NOT NULL).
- Flyway는 각 서비스 부팅 시 자동 실행, Stg/Prod는 별도 마이그레이션 Job(`infra:batch`)에서 일괄 수행.

---

## 7. CI/CD — GitHub Actions 베이스라인

### 7.1 워크플로 구조

```
.github/workflows/
├── ci-backend.yml          # PR 트리거: lint/build/test/sca/openapi/coverage
├── ci-frontend.yml         # PR 트리거: lint/build/test/e2e-smoke/lighthouse
├── cd-dev.yml              # develop 머지: image 빌드 + 푸시 + ArgoCD 동기
├── cd-stg.yml              # release 브랜치: 수동 승인 + 배포
├── cd-prod.yml             # main 머지 + PM 승인: Blue-Green 배포
├── nightly-security.yml    # cron 02:00: ZAP DAST + dependency 풀스캔
└── codegen-sync.yml        # OpenAPI 변경 시 Frontend codegen 자동 PR
```

### 7.2 ci-backend.yml 골격

```yaml
name: CI Backend
on:
  pull_request:
    paths: ["tulip-backend/**"]
  push:
    branches: [develop, main]
    paths: ["tulip-backend/**"]

permissions:
  contents: read
  pull-requests: write
  security-events: write

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: '21' }
      - uses: gradle/actions/setup-gradle@v3
      - run: ./gradlew spotlessCheck checkstyleMain

  build-test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:15.7-alpine
        env:
          POSTGRES_PASSWORD: test
        ports: ['5432:5432']
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: '21' }
      - uses: gradle/actions/setup-gradle@v3
      - run: ./gradlew build test integrationTest jacocoTestReport
      - uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: '**/build/reports/**'

  sonar:
    runs-on: ubuntu-latest
    needs: build-test
    steps:
      - uses: actions/checkout@v4
      - run: ./gradlew sonar
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with: { scan-type: fs, severity: CRITICAL,HIGH }
      - uses: snyk/actions/gradle@master
        env: { SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }} }

  openapi-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npx --yes @stoplight/spectral-cli lint 'services/*/openapi/**/*.yaml'

  container-build:
    runs-on: ubuntu-latest
    needs: [build-test, sca]
    if: github.event_name == 'push'
    strategy:
      matrix:
        service: [iam, tenant, member, code-policy, notification, file]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: services/${{ matrix.service }}-service
          push: true
          platforms: linux/amd64,linux/arm64
          tags: |
            ghcr.io/tulip-plus/${{ matrix.service }}-service:${{ github.sha }}
            ghcr.io/tulip-plus/${{ matrix.service }}-service:${{ github.ref_name }}
      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/tulip-plus/${{ matrix.service }}-service:${{ github.sha }}
          severity: CRITICAL,HIGH
          exit-code: '1'
```

### 7.3 ci-frontend.yml 골격

```yaml
name: CI Frontend
on:
  pull_request:
    paths: ["tulip-frontend/**"]
  push:
    branches: [develop, main]
    paths: ["tulip-frontend/**"]

jobs:
  build-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: tulip-frontend
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
          cache-dependency-path: 'tulip-frontend/pnpm-lock.yaml'
      - run: pnpm install --frozen-lockfile
      - run: pnpm turbo run lint type-check test build
      - run: pnpm turbo run test:e2e -- --grep "@smoke"
      - uses: treosh/lighthouse-ci-action@v11
        with:
          urls: |
            http://localhost:3000/
            http://localhost:3000/dashboard
          uploadArtifacts: true
```

### 7.4 SCA·보안 단계 요약

| 도구 | 단계 | 차단 기준 |
|---|---|---|
| Spotless / Checkstyle | lint | 위반 시 차단 |
| ESLint / Prettier | lint | 위반 시 차단 |
| Spectral | OpenAPI lint | 룰 위반 차단 |
| JaCoCo / Vitest coverage | test | 신규 코드 80% 미달 차단 |
| Sonar | 정적 분석 | Quality Gate 실패 차단 |
| Trivy (fs) | SCA | Critical 차단 |
| Trivy (image) | container | Critical/High 차단 |
| Snyk | dependency | Critical 차단 |
| Gitleaks | secret scan | 위반 차단 |
| OWASP ZAP | nightly DAST | High 발견 시 Issue 자동 생성 |

---

## 8. 컨테이너 레지스트리·태깅 정책

### 8.1 레지스트리

| 환경 | 레지스트리 |
|---|---|
| Dev/Stg/Prod | **GitHub Container Registry (`ghcr.io/tulip-plus/*`)** Phase 1 |
| 후속 검토 | AWS ECR (Y2, 멀티 클라우드 시) |

### 8.2 태깅 규칙

| 태그 | 의미 | 예 |
|---|---|---|
| `<git-sha>` | 불변 빌드 식별자 (모든 빌드) | `ghcr.io/tulip-plus/member-service:a1b2c3d` |
| `<branch>` | 최신 브랜치 빌드 | `:develop`, `:main` |
| `v<MAJOR>.<MINOR>.<PATCH>` | 릴리스 태그 (SemVer) | `:v1.0.0` |
| `v<MAJOR>.<MINOR>` | 마이너 트랙 floating | `:v1.0` |
| `latest` | **미사용** (불변성 보장 위반) | - |
| `stg`, `prod` | 환경 별칭 (ArgoCD 운영) | `:prod` |

### 8.3 이미지 SBOM·서명

- `cosign` + GitHub OIDC로 이미지 서명 (Phase 1 도입)
- `syft`로 SBOM 생성 → 릴리스 아티팩트 첨부

---

## 9. 개발자 환경 셋업 명령

### 9.1 Makefile

```makefile
.PHONY: help up down seed dev clean rebuild logs ps fmt test e2e codegen

help:                ## 사용 가능한 명령 표시
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up:                  ## 모든 인프라 컨테이너 기동 (PG/Redis/Kafka/Keycloak/MinIO/Mailhog/Obs/OS)
	docker compose -f infra/compose/docker-compose.yml up -d
	./scripts/wait-for-healthy.sh

down:                ## 모든 컨테이너 정지·삭제
	docker compose -f infra/compose/docker-compose.yml down

clean: down          ## 볼륨까지 완전 초기화
	docker compose -f infra/compose/docker-compose.yml down -v

seed:                ## 샘플 시드 데이터 적재 (테넌트 2 + 회원 100 + 코드 마스터)
	./scripts/seed.sh

migrate:             ## Flyway 마이그레이션 모든 서비스에 적용
	cd tulip-backend && ./gradlew flywayMigrate

dev:                 ## 개발 모드 (백엔드 + 프론트엔드 동시 hot-reload)
	$(MAKE) -j 2 dev-backend dev-frontend

dev-backend:         ## 백엔드 핵심 서비스 dev 프로필로 기동
	cd tulip-backend && ./gradlew :services:tenant-service:bootRun :services:iam-service:bootRun :services:member-service:bootRun --parallel

dev-frontend:        ## 프론트 admin + opac 동시 dev
	cd tulip-frontend && pnpm turbo run dev --parallel

fmt:                 ## 포맷팅 (Spotless + Prettier)
	cd tulip-backend && ./gradlew spotlessApply
	cd tulip-frontend && pnpm turbo run lint -- --fix

test:                ## 모든 단위/통합 테스트
	cd tulip-backend && ./gradlew test integrationTest
	cd tulip-frontend && pnpm turbo run test

e2e:                 ## Playwright E2E
	cd tulip-frontend && pnpm turbo run test:e2e

codegen:             ## OpenAPI → TypeScript 클라이언트 재생성
	cd tulip-frontend && pnpm turbo run codegen

logs:                ## 컨테이너 로그 follow
	docker compose -f infra/compose/docker-compose.yml logs -f

ps:                  ## 컨테이너 상태
	docker compose -f infra/compose/docker-compose.yml ps

rebuild:             ## 백엔드 이미지 재빌드
	cd tulip-backend && ./gradlew bootBuildImage
```

### 9.2 첫날 신규 개발자 절차

```bash
# 1. 리포 clone
git clone https://github.com/tulip-plus/tulip.git
cd tulip

# 2. 사전조건 체크 (Docker 24+, Java 21, Node 20, pnpm 9)
./scripts/check-prereq.sh

# 3. 인프라 기동
make up

# 4. 시드
make seed

# 5. 개발 시작
make dev

# 6. 브라우저
open http://localhost:3000           # Admin
open http://localhost:3100           # OPAC
open http://localhost:8080           # Keycloak (admin / admin_local)
open http://localhost:8025           # Mailhog
open http://localhost:9001           # MinIO Console
open http://localhost:3001           # Grafana (admin / admin_local)
open http://localhost:5601           # OpenSearch Dashboards
```

### 9.3 `.env` 표준

```bash
# tulip-backend/.env.example
TULIP_DB_URL=jdbc:postgresql://localhost:5432/tulip
TULIP_DB_USER=tulip
TULIP_DB_PASSWORD=tulip_local
TULIP_REDIS_URL=redis://localhost:6379
TULIP_KAFKA_BROKERS=localhost:9092
TULIP_KEYCLOAK_URL=http://localhost:8080
TULIP_KEYCLOAK_REALM=tulip
TULIP_S3_ENDPOINT=http://localhost:9000
TULIP_S3_ACCESS_KEY=tulip
TULIP_S3_SECRET_KEY=tulip_local_minio
TULIP_OTEL_ENDPOINT=http://localhost:4318
TULIP_MAIL_HOST=localhost
TULIP_MAIL_PORT=1025
```

```bash
# tulip-frontend/.env.example (NEXT_PUBLIC_ 만 클라이언트 노출)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8090/api
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8080
NEXT_PUBLIC_KEYCLOAK_REALM=tulip
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=admin-web
```

---

## 10. 환경별 차이 요약

| 항목 | Local | Dev | Stg | Prod |
|---|---|---|---|---|
| 인프라 | Docker Compose | K8s `tulip-dev` | K8s `tulip-stg` | K8s `tulip-prod` Multi-AZ |
| DB | PG 단일 컨테이너 | PG 단일 RDS-like | PG Primary + Replica | PG Primary + 2 Replica + DR |
| Kafka | 단일 노드 | 3 노드 | 3 노드 | 5 노드 Multi-AZ |
| Redis | 단일 | Replica 1 | Sentinel | Cluster |
| Keycloak | dev mode | clustered 1 | clustered 2 | clustered 3 |
| 옵저버빌리티 | 로컬 stack | 동일 stack | 동일 stack | + 알람·SIEM |
| Secret | `.env` | K8s Secret | Vault | Vault + KMS |
| 배포 | `make` | 자동 (develop) | 수동 승인 | PM 승인 + Blue-Green |

---

## 11. 결정 이력 (ADR 후보)

| 후보 ADR | 결정 |
|---|---|
| ADR-011 | Gradle Multi-Project + Kotlin DSL + Version Catalog 채택 |
| ADR-012 | pnpm Workspace + Turborepo 채택 (Yarn/Nx 미채택) |
| ADR-013 | Java 21 + Spring Boot 3.3 LTS 라인 채택 |
| ADR-014 | Next.js 15 App Router + Tailwind 4 + shadcn/ui 채택 |
| ADR-015 | OpenSearch 2.x (Elasticsearch 미채택) — 라이센스 + nori |
| ADR-016 | Flyway 10 채택 (Liquibase 미채택) |
| ADR-017 | GitHub Container Registry 채택 (Phase 1) |
| ADR-018 | Phase 1은 단일 DB + 스키마 분리, 도메인별 DB 분리는 옵션 |
| ADR-019 | Kafka Zookeeper 모드 1차, KRaft 모드 Phase 2 마이그레이션 |
| ADR-020 | `@hey-api/openapi-ts`로 OpenAPI → TS 코드 생성 |

각 ADR은 `docs/04_dev_lead/adr/ADR-NNN-<title>.md`로 별도 작성 예정.

---

## 12. 후속 작업

| 산출물 | 담당 | 시점 |
|---|---|---|
| `buildSrc/` convention plugin 코드 | DevLead | Sprint 1-A 1주차 |
| `tulip-bom` 의존성 BOM 코드 | DevLead | Sprint 1-A 1주차 |
| `tulip-common-*` 6개 모듈 스켈레톤 | DevLead + BackendSenior | Sprint 1-A 2주차 |
| `docker-compose.yml` + init scripts | DevLead + DBA | Sprint 1-A 1주차 |
| Keycloak Realm export JSON | BackendSenior + DevLead | Sprint 1-B 1주차 |
| GitHub Actions YAML 4종 | DevLead | Sprint 1-A 2주차 |
| `apps/admin` + `apps/opac` 골격 | FrontendSenior | Sprint 1-A 2주차 |
| `@tulip/ui` 20개 컴포넌트 | FrontendSenior + FrontendDev | Sprint 1-D |
| `@tulip/api-client` codegen 자동화 | FrontendSenior + BackendSenior | Sprint 1-C ~ 1-D |
| ADR-011 ~ ADR-020 개별 문서화 | DevLead | Phase 1 진행 중 |

---

## 13. 변경 이력

| 버전 | 일자 | 변경 내용 | 작성자 |
|---|---|---|---|
| v0.1 | 2026-05-11 | Phase 0 초안 — 백엔드/프론트엔드/인프라/CI 결정 종합 | DevLead Agent |
