# tenant-service (Sprint 1-C)

Tulip+ 테넌트·라이브러리·분관·테넌트 설정 마스터 + Outbox 이벤트 발행 서비스.

- 포트: **8102**
- DB 스키마: `tnt_*` (DBA 작성 `V1__tenant_init.sql`)
- 패키지: `com.tulip.tenant.*`
- 담당: BackendSenior (구현) / DBA (스키마·RLS)

---

## 1. 빌드 / 실행

```bash
# 단위 테스트만 (CI 기본)
./gradlew :services:tenant-service:test

# Testcontainers 가 필요한 통합 테스트(docker 필요)
./gradlew :services:tenant-service:integrationTest

# 부트 실행 (docker compose 인프라가 켜져 있어야 함)
./gradlew :services:tenant-service:bootRun
```

---

## 2. 엔드포인트 카탈로그

### 시스템 관리자 전용 (`hasRole('SYS_ADMIN')`)

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/tenants` | 테넌트 생성 |
| GET | `/api/v1/tenants` | 테넌트 검색 (offset/limit, code/name/status) |
| GET | `/api/v1/tenants/{id}` | 단건 조회 |
| PATCH | `/api/v1/tenants/{id}` | 상태·플랜·기본정보 변경 |
| DELETE | `/api/v1/tenants/{id}` | 소프트 삭제 (SUSPENDED → CLOSED) |

> SYS_ADMIN 토큰 + 헤더 `X-Sys-Bypass: true` 조합으로 RLS 우회 진입.

### 자기 테넌트 (`hasAnyRole('TENANT_ADMIN','SYS_ADMIN')`)

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/tenants/me` | 현재 테넌트 |
| PATCH | `/api/v1/tenants/me` | 자기 테넌트 정보 수정 (status 는 SYS_ADMIN 만) |
| GET | `/api/v1/tenants/me/settings` | 설정 KV 목록 |
| GET | `/api/v1/tenants/me/settings/{key}` | 설정 단건 |
| PUT | `/api/v1/tenants/me/settings/{key}` | 설정 upsert |

### 라이브러리·분관 (`hasAnyRole('TENANT_ADMIN','LIB_ADMIN','SYS_ADMIN')`)

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/libraries` | 라이브러리 생성 |
| GET | `/api/v1/libraries` | 검색 |
| GET | `/api/v1/libraries/{id}` | 단건 조회 |
| PATCH | `/api/v1/libraries/{id}` | 수정 |
| DELETE | `/api/v1/libraries/{id}` | 소프트 삭제 (활성 분관 존재 시 422) |
| POST | `/api/v1/libraries/{libId}/branches` | 분관 생성 |
| GET | `/api/v1/libraries/{libId}/branches` | 분관 목록 |
| PATCH | `/api/v1/branches/{id}` | 분관 수정 |
| DELETE | `/api/v1/branches/{id}` | 분관 소프트 삭제 |

### 내부 서비스용 (`hasAuthority('SCOPE_internal')`)

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/internal/tenants/{id}/exists` | 테넌트 존재 확인 |
| GET | `/api/v1/internal/libraries/{id}/context` | 라이브러리 메타 컨텍스트 |

---

## 3. Outbox 이벤트 토픽

토픽 명명 규칙: `tulip.tenant.{aggregateType}.{event}` (Kafka 키: `aggregateId` = ULID)

| 이벤트 타입 | 토픽 |
|---|---|
| `tenant.created` | `tulip.tenant.tenant.created` |
| `tenant.updated` | `tulip.tenant.tenant.updated` |
| `tenant.status_changed` | `tulip.tenant.tenant.status_changed` |
| `library.created` | `tulip.tenant.library.created` |
| `library.updated` | `tulip.tenant.library.updated` |
| `library.deleted` | `tulip.tenant.library.deleted` |
| `library_branch.created` | `tulip.tenant.library_branch.created` |
| `library_branch.updated` | `tulip.tenant.library_branch.updated` |

페이로드는 JSON 문자열. 헤더 `traceId`, `tenantId`, `eventType` 부착.

---

## 4. RLS 동작 메모

- 모든 변경 트랜잭션 시작 시 MyBatis 인터셉터(`RlsMyBatisInterceptor`)가
  `set_config('app.current_tenant', :tenantId, true)` 와
  `set_config('app.role', :role, true)` 를 실행 — `SET LOCAL` 등가.
- 결과: PostgreSQL RLS 정책 (`tenant_id = fn_current_tenant_id()`) 이 자동 격리.
- 시스템 관리자(`@SystemAdmin` 표기 + `X-Sys-Bypass: true`) 의 경우
  `app.role = 'SYS_ADMIN'` 로 `tnt_tenant` 4-policy 통과.
- Outbox Poller 는 `RlsSessionApplier.applySysAdmin()` 으로 백그라운드 컨텍스트 부여.

---

## 5. 디렉토리 구조

```
src/main/java/com/tulip/tenant/
  api/             # REST controller + DTO
  application/     # 도메인 service
  config/          # Security / MyBatis / Kafka 설정
  domain/          # Tenant / Library / LibraryBranch / TenantSetting
  error/           # TenantErrorCode (TLP-TNT-*)
  infra/mapper/    # MyBatis mapper interface (+ params)
  outbox/          # Appender / Poller / Publisher / RlsSessionApplier
  security/        # AuthFilter / TenantSessionContext / @SystemAdmin

src/main/resources/
  application.yml
  mapper/*.xml
  db/migration/V1__tenant_init.sql  # DBA 작성
```

---

## 6. Phase 1-C DoD 매핑

- [x] 테넌트 CRUD + 라이브러리 CRUD + 분관 CRUD + 설정 KV
- [x] Outbox 패턴 (PENDING → PROCESSING → COMPLETED, retry 5회)
- [x] Kafka 토픽 발행 (도메인 이벤트 8종)
- [x] PostgreSQL RLS 세션 변수 자동 적용
- [x] 시스템 관리자 bypass 모드 (`X-Sys-Bypass: true`)
- [x] OpenAPI(springdoc) 자동 노출 + Gateway 라우팅
- [ ] RLS 회귀 매트릭스 1만건 — QA + DBA 합동 (별도 트랙)
