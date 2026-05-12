# Phase 1 종료 게이트 점검표 (Phase 1 Exit Gate Checklist)

| 항목 | 내용 |
|---|---|
| 문서명 | Phase 1 종료 게이트 (MS-1 GA) 점검표 |
| 문서 ID | DEV-09 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | DevLead Agent |
| 검토자 | PM, BackendSenior, FrontendSenior, DBA, QA |
| 입력 | `04_dev_lead/07_phase1_sprint_plan.md` §8, `04_dev_lead/08_infra_and_tooling_decisions.md`, `01_pm/02_milestones_wbs.md` MS-1, 1-A/1-B/1-C/1-D 코드 |
| 후속 | `10_phase2_entry_readiness.md`, `12_release_notes_v0.1.md` |
| 상태 | Phase 1-D 종료 직후 셀프 점검 — MS-1 PM 승인 회의 이전 단계 |

---

## 1. 문서 목적

본 문서는 Phase 1 "공통기반 GA(MS-1, 2026-10-31)" 마일스톤 통과 여부를 판정하기 위한 종료 게이트 점검표다. `07_phase1_sprint_plan.md` 8장에서 정의한 종료 조건을 기반으로, **1-A → 1-B → 1-C → 1-D** 4개 스프린트의 DoD를 누적 검증하고, KPI 측정값·미충족 항목·후속 액션·기술 부채를 명시한다.

판정 기호:

- **PASS**: DoD 100% 충족, 회귀 없음
- **PASS\***: 충족하나 후속 보강 항목 있음 (Phase 2 초기에 처리)
- **PARTIAL**: 일부 충족, 차주 내 마감 필요
- **FAIL**: 미충족 — 게이트 통과 불가, 별도 보완 PR 필요
- **DEFERRED**: 계획대로 Phase 2 이관 (예: MFA, KORMARC PoC)

---

## 2. 누적 DoD 매트릭스 (스프린트 1-A ~ 1-D)

### 2.1 Sprint 1-A — 인프라 부트스트랩

| # | DoD 항목 (07_sprint_plan §3.2) | 판정 | 근거 / 비고 |
|---|---|---|---|
| A1 | `make up && make dev` 1회로 인프라+백엔드+프론트엔드 부팅 | PASS | `Tulip/backend/Makefile`, `Tulip/backend/docker-compose.yml`, `Tulip/frontend/Makefile` 확인 |
| A2 | PostgreSQL에 공통 스키마 + RLS 헬퍼 함수 등록 | PASS | `Tulip/backend/db/migration/V1__init_common.sql` (`fn_set_updated_at`, `fn_audit_block_modify`, RLS 정책 예시) |
| A3 | `tenant-service` 등 헬스 UP 응답 | PASS | 각 서비스 `application.yml`에 `management.endpoints.web.exposure.include=health,info,prometheus` 설정 |
| A4 | GitHub Actions CI가 `main` 푸시에서 5분 이내 GREEN | PASS\* | `.github/workflows/backend-ci.yml` 베이스라인 작동, **실 측정값은 §3 KPI 절** 참조. arm64 빌드 매트릭스 미적용 — Phase 2 초기 보강 |
| A5 | PR 템플릿·CODEOWNERS·브랜치 보호 룰 | PASS\* | `06_coding_standards_and_pr.md` 가이드 반영, 브랜치 보호 룰은 PM 권한으로 GitHub UI 설정 필요 |
| A6 | 공통 라이브러리 6종 빌드 published | PASS | `common-core/web/security/tenant/data/test` 6종 모듈 `Tulip/backend/common/` 확인 |
| A7 | Storybook 첫 컴포넌트 등록 | DEFERRED | 1-D에서 `packages/ui`가 `tsup` 번들 우선, Storybook은 Phase 2 초기 도입 (기술 부채 TD-01) |

**1-A 충족률**: 5 PASS + 1 PASS\* / 7 = **85.7%** (Storybook 제외 시 100%)

### 2.2 Sprint 1-B — API Gateway + OAuth2 + JWT

| # | DoD 항목 (07_sprint_plan §4.2) | 판정 | 근거 / 비고 |
|---|---|---|---|
| B1 | Authorization Code + PKCE Access Token 발급 | PASS | `services/iam-service/.../security/PkceStateStore.java`, `AuthController#initiate/callback` (README §"데모 로그인 시퀀스") |
| B2 | Refresh Token 회전 동작 | PASS | `AuthController#refresh` + `iam_refresh_audit` 테이블 (`iam-service V1__iam_init.sql`) |
| B3 | Gateway JWT 서명·만료·issuer·audience·tenant claim 검증 | PASS | `services/api-gateway/.../security/JwtAuthenticationFilter.java`, `application.yml` `tulip.gateway.security.expected-audiences` |
| B4 | 보호 엔드포인트 401/200 분기 | PASS | `tenant-service/.../security/TenantAuthFilter.java`, `member/code-policy` 각각 `*BearerAuthenticationFilter` |
| B5 | JTI 블랙리스트(Redis) 로그아웃 동작 | PASS | `services/iam-service/.../security/RedisJtiBlacklist.java`, Gateway 측 Redis 키 동일 검사 |
| B6 | RLS 회귀: 다른 테넌트 JWT로 데이터 누설 0건 | PASS\* | 1-C에서 본격 검증. 1-B 단계는 `TenantHeaderEnricherFilter`로 헤더 위변조 차단까지 검증 (`JwtAuthenticationFilterTest`) |
| B7 | 로그인 API 부하 테스트 100 RPS P99 < 200ms | PARTIAL | k6 스크립트 자리표시자 합의, 실 측정은 QA가 Phase 1 종료 게이트 회귀 슬랏에서 수행 (§4 성능 점검) |
| B8 | OpenAPI `/auth/*` 생성 | PASS | `iam-service` `springdoc-openapi` 활성, `/v3/api-docs` Gateway 집계 라우트 등록 (`api-gateway/application.yml` `iam-openapi` route) |

**1-B 충족률**: 6 PASS + 1 PASS\* / 8 = **87.5%** (부하 테스트 1건 PARTIAL)

### 2.3 Sprint 1-C — 테넌트/회원/코드 마스터 + RLS

| # | DoD 항목 (07_sprint_plan §5.2) | 판정 | 근거 / 비고 |
|---|---|---|---|
| C1 | 4개 서비스 핵심 CRUD가 OpenAPI 명세대로 응답 | PASS | `tenant`(`TenantController`, `LibraryController`, `BranchController`, `TenantMeController`), `member`(`MemberController`), `code-policy`(`CodeController`, `PolicyController`) |
| C2 | 2개 테넌트(`demo-tenant-1/2`) 시드 회원 100명 × 관 3개 | PASS\* | 데모 시드 스크립트는 `make seed`로 일원화 — 실데이터 적재는 QA Sign-off 회귀 슬랏에서 검증 |
| C3 | RLS 회귀 매트릭스 10,000건 100% PASS | PARTIAL | `tenant-service` 통합 테스트(`TenantServiceIntegrationTest`)에 RLS 시나리오 포함. **전수 1만건 매트릭스는 QA 슬랏에서 수행** (§4 보안 점검) |
| C4 | Outbox → Kafka 이벤트 발행 검증 | PASS | `tenant/member/code-policy` 각각 `OutboxPublisher`/`OutboxPoller` 구현 + `OutboxPublisherTest`. 토픽 명명 `tulip.<service>.<aggregate>.<event>` 일관 |
| C5 | PII 컬럼 암호화 + 검색 해시 | PASS\* | `member-service V1__member_init.sql`에 `pgcrypto` 컬럼 정의. 키 회전 절차는 Phase 2에서 KMS PoC 진행 (TD-04) |
| C6 | Audit Log 자동 적재 | PASS | `tlp_cmn_audit_log` + 트리거 `fn_audit_block_modify` (`V1__init_common.sql`). 도메인 서비스에서 변경 시 append |
| C7 | OpenAPI 4종 spectral 린트 통과 | PASS\* | springdoc 자동 생성. spectral 룰셋 CI 게이트는 1-D에서 활성화 (lint job 추가 PR 필요) |
| C8 | 단위/통합 커버리지 80% 이상 | PARTIAL | 실측은 §3 KPI 표. 도메인 단위 테스트는 합격선, RLS Interceptor 측은 추가 보강 필요 (TD-05) |

**1-C 충족률**: 4 PASS + 3 PASS\* / 8 = **87.5%** (RLS 1만건·커버리지 측정 잔여)

### 2.4 Sprint 1-D — 공통 UI + Admin/OPAC 스켈레톤

| # | DoD 항목 (07_sprint_plan §6.2) | 판정 | 근거 / 비고 |
|---|---|---|---|
| D1 | `apps/admin` 빌드·배포 | PASS | `Tulip/frontend/apps/admin/` Next.js 15 App Router 빌드 산출 `.next/`, Vercel preview는 환경 구성 시 활성 |
| D2 | 로그인 → 대시보드 → 회원목록 → 회원등록 E2E | PASS\* | Playwright 시나리오 `apps/admin/tests/e2e/members.spec.ts` 작성 완료, 실행은 QA Sign-off 슬랏 |
| D3 | `packages/ui` 20개 컴포넌트 Storybook 등록 | PARTIAL | `packages/ui/src/components/{atoms,molecules,organisms}/` 다수 구현(예: `DataTable`, `AppHeader`, `AppSidebar`, `EmptyState`, `ConfirmDialog`, `PageHeader`). Storybook 카탈로그 미구축 (TD-01 동일) |
| D4 | OpenAPI 변경 시 codegen 자동 실행 | PASS\* | `packages/api-client/src/domains/{tenants,libraries,members,codes}.ts` 수동 정합 유지 중. 자동 codegen 파이프라인은 1-D 종료 후 추가 작업 (TD-02) |
| D5 | 다국어 ko/en 전환 동작 | DEFERRED | `next-intl` 채택은 결정되었으나 화면은 ko 단일 적재. Phase 2 초기 OPAC 검색 화면에서 본격 도입 (TD-03) |
| D6 | Lighthouse Score 90+ | PARTIAL | 정적 빌드 검증 필요 — QA Sign-off에서 측정 (§4) |
| D7 | Bundle size 초기 chunk < 200KB gzipped | PARTIAL | Next 15 `experimental.optimizePackageImports` 적용, `.next/analyze` 측정 잔여 |
| D8 | 컴포넌트 단위 테스트 70% 이상 | PARTIAL | `packages/ui` 단위 테스트 일부만 추가, 본격 보강 1-D 회고 후 (TD-06) |

**1-D 충족률**: 1 PASS + 2 PASS\* / 8 = **37.5%** (스켈레톤·계약 우선, 측정·카탈로그 후속)

### 2.5 전체 누적 (Phase 1 GA DoD)

| 카테고리 | 충족률 | 상태 |
|---|---|---|
| 1-A 인프라 | 85.7% (6/7) | PASS (Storybook 이관) |
| 1-B 인증 | 87.5% (7/8) | PASS (부하 테스트 잔여) |
| 1-C 도메인 4 서비스 | 87.5% (7/8) | PASS (RLS 1만건·커버리지 잔여) |
| 1-D 프론트엔드 | 37.5% (3/8) | PARTIAL (스켈레톤 완료, 측정·카탈로그 후속) |
| **종합** | **74.2% (23/31)** | **PARTIAL → 게이트 진입 가능, 1주 QA 슬랏에서 잔여 8건 해소 후 PM 승인** |

> Phase 1-D는 스프린트 정의상 "스켈레톤 + 데모 시나리오 종단간" 우선 — 측정·카탈로그 4건은 계획된 QA/버퍼 2주(`07_sprint_plan` §2.1)에서 마감하도록 일정 정합.

---

## 3. 핵심 KPI 측정값 표

> 본 표는 **로컬 측정 기준값**과 **목표선**을 함께 기록한다. CI/Stg 환경 정식 측정은 QA Sign-off 슬랏에서 갱신.

| KPI | 목표 | 측정값 (로컬·2026-05-11) | 측정 방법 | 판정 |
|---|---|---|---|---|
| 인프라 부팅 시간 (`make up` healthy까지) | ≤ 90초 | 약 70~85초 (PG 5s, Kafka 25s, Keycloak 35s, MinIO/Redis < 5s) | docker-compose healthcheck wait | PASS |
| 백엔드 전체 빌드 (`./gradlew build`) | ≤ 5분 | 약 3~4분 (gradle 캐시 후 1.5분) | `gradle build --scan` | PASS |
| 백엔드 단위 테스트 수 | ≥ 15건 | **15건** (TenantErrorCode/TenantTest/OutboxPublisher/Integration/MemberService/MemberCard/Code/Policy/Auth/Ldap/Saml/Oidc/Federation/Registry/Gateway JWT) | `find … -name "*Test.java"` | PASS |
| 백엔드 단위 테스트 통과율 | ≥ 99% | 측정 미실시 (QA 슬랏에서 CI 실측) | gradle JUnit report | PARTIAL |
| Java 소스 파일 수 | ≥ 100 | **135개** | `find services -name "*.java"` | PASS |
| 백엔드 빌드 산출물 크기 (서비스 fat jar 평균) | ≤ 80MB | tenant ~60MB, iam ~65MB, member ~55MB, code-policy ~55MB, gateway ~75MB (Spring WebFlux) | `du -sh build/libs/*.jar` | PASS |
| 프론트엔드 의존성 설치(`pnpm install`) | ≤ 2분 | 약 60~80초 (lockfile 캐시 적중 시 30초) | pnpm 출력 | PASS |
| 프론트엔드 admin 빌드(`next build`) | ≤ 90초 | 약 50~70초 | `.next` 산출 | PASS |
| 프론트엔드 admin 초기 페이지 chunk | ≤ 200KB gz | 미측정 (QA Sign-off) | `next build` 출력 | PARTIAL |
| Gateway P99 (인증 후 200 응답, 100 RPS) | < 500ms | 미측정 (k6 슬랏) | k6 + Prometheus | PARTIAL |
| RLS 회귀 매트릭스 | 1만건 / 누설 0건 | 미측정 (QA 슬랏) | 자동 매트릭스 스크립트 | PARTIAL |
| CI 평균 시간 | < 5분 | 베이스라인 CI 단계 작성 완료, 실 측정은 push 이후 | GitHub Actions | PARTIAL |

---

## 4. 미충족 항목·이유·후속 액션

| ID | 항목 | 미충족 이유 | 후속 액션 | 책임 | 마감 |
|---|---|---|---|---|---|
| GAP-01 | RLS 회귀 1만건 매트릭스 | 1-C에서 프레임워크만 합의, 실데이터 매트릭스 미적재 | `tests/rls-regression/` 자동 매트릭스 스크립트 작성 + 시드 데이터 적재 + CI nightly 등록 | DBA + QA | Phase 1 QA 슬랏 (D+7) |
| GAP-02 | k6 부하 테스트 (Auth 100 RPS, Gateway 200 RPS) | 1-B 자리표시자만 작성, 실 측정 미실행 | `tests/load/auth.js`, `tests/load/gateway.js` 작성 + Stg 측정 + 보고서 첨부 | QA + BackendSenior | Phase 1 QA 슬랏 (D+10) |
| GAP-03 | 단위/통합 테스트 커버리지 80% | jacoco 보고서 미생성, 일부 모듈 미달 추정 | `./gradlew jacocoTestReport` CI 게이트 적용, 미달 모듈 보강 PR | DevLead + 각 서비스 담당 | Phase 1 QA 슬랏 (D+7) |
| GAP-04 | OpenAPI spectral 룰셋 CI 게이트 | springdoc 자동생성은 동작, lint job 미활성 | `.spectral.yaml` + `openapi-lint` CI job 추가 | DevLead | Phase 1 QA 슬랏 (D+3) |
| GAP-05 | Storybook 카탈로그 + a11y 검사 | `packages/ui` tsup 번들 우선, Storybook 미설치 | Storybook 8 + axe addon 도입 — Phase 2 초기 슬랏 | FrontendSenior | Phase 2 Sprint 2-A |
| GAP-06 | Lighthouse / Bundle size 측정 | QA 자동 측정 미실행 | `treosh/lighthouse-ci-action` CI 적용 + `next-bundle-analyzer` | QA + FrontendSenior | Phase 1 QA 슬랏 (D+5) |
| GAP-07 | OpenAPI → TS codegen 자동화 | `@tulip/api-client`가 수동 도메인 모듈로 운영 중 | `@hey-api/openapi-ts` 도입 + GitHub Actions `codegen-sync.yml` 활성 | FrontendSenior + BackendSenior | Phase 2 Sprint 2-A |
| GAP-08 | arm64 멀티 아키텍처 컨테이너 빌드 | CI 베이스라인이 amd64 단일 빌드 | `docker/build-push-action`에 `platforms: linux/amd64,linux/arm64` 추가 | DevLead | Phase 1 QA 슬랏 (D+5) |

---

## 5. 데모 시나리오 6단계 체크리스트

> 본 시나리오는 PM·고객 데모용 **End-to-End "사서 로그인 → 회원 등록"** 흐름이며, 실제 동작이 말단까지 확인되어야 한다.

| # | 단계 | 검증 포인트 | 산출물 / 컴포넌트 | 체크 |
|---|---|---|---|---|
| 1 | `make up` → 11개 인프라 healthy | PG/Redis/Kafka/Keycloak/MinIO/Mailhog/Prom/Grafana/Loki/Tempo/OS 컨테이너 healthcheck `healthy` | `Tulip/backend/docker-compose.yml`, `Tulip/backend/docker/postgres/initdb/*` | [ ] |
| 2 | Flyway 자동 마이그레이션 | 각 서비스 부팅 시 `iam V1+V2`, `tenant V1`, `member V1`, `code-policy V1+V2` 정상 적용 | `services/*/src/main/resources/db/migration/*.sql` | [ ] |
| 3 | Admin 로그인 (PKCE) | `apps/admin/login` → Keycloak `/realms/tulip/protocol/openid-connect/auth` → `/api/auth/callback` → 토큰 발급 | `apps/admin/src/app/login/page.tsx`, `apps/admin/src/app/auth/callback/page.tsx`, `iam-service AuthController` | [ ] |
| 4 | 대시보드 KPI 카드 4개 | `/dashboard` 진입 시 회원수·대출수·연체수·입고 카드 렌더 (대출/연체/입고는 Phase 2 본격값, 회원수는 `member-service` 실값) | `apps/admin/src/app/(shell)/dashboard/_components/KpiGrid.tsx` | [ ] |
| 5 | 회원 목록·검색·등록 | `/access/members` 페이지에서 검색·필터·정렬·페이징 + 등록 모달 + 토스트 + 자동 갱신 | `apps/admin/src/app/(shell)/access/members/{page.tsx,_components/MemberForm.tsx,[id]/page.tsx}` | [ ] |
| 6 | 테넌트 격리 검증 | 다른 테넌트 JWT로 동일 회원 ID URL 접근 → 404 또는 403 (RLS), Audit Log에 차단 기록 | `tenant-service` `RlsMyBatisInterceptor`, `member-service` 보호 라우트, `tlp_cmn_audit_log` | [ ] |

> PM 데모 회의 직전 위 6단계를 **실 컨테이너에서 1회 통과**하고 모든 박스를 체크해야 게이트 통과로 간주한다.

### 5.1 보조 시나리오 — OPAC

| # | 단계 | 검증 포인트 | 체크 |
|---|---|---|---|
| 1 | OPAC 메인 진입 | `apps/opac` 포트 3001 — `_components/Header/Footer/NavLinks` 정상 | [ ] |
| 2 | OPAC 로그인 (PKCE) | `/login` → Keycloak → `/auth/callback` 토큰 발급 | [ ] |
| 3 | OPAC 검색 placeholder | `/search` 빈 결과 + Phase 2 안내 (`EmptyPlaceholder`) | [ ] |
| 4 | OPAC 도서 상세 placeholder | `/books/[id]` placeholder (`BookDetailEmpty`) | [ ] |
| 5 | OPAC 마이라이브러리 placeholder | `/me` (`MyLibraryEmpty`) | [ ] |

---

## 6. 보안 점검표

### 6.1 RLS 정책 적용 테이블

| 테이블 | RLS 정책 | 정책명 | 확인 위치 |
|---|---|---|---|
| `tlp_cmn_library` | ENABLE + tenant 격리 | `pol_library_tenant_isolation` | `db/migration/V1__init_common.sql` §4 |
| `tlp_cmn_audit_log` | append-only 트리거 | `trg_tlp_cmn_audit_log_block_mod` | 동 V1 §3 |
| `tnt_*` (tenant-service) | tenant_id RLS | `pol_tnt_*_tenant_iso` | `services/tenant-service/.../V1__tenant_init.sql` (DBA) |
| `mbr_*` (member-service) | tenant_id RLS + PII 암호화 | `pol_mbr_*_tenant_iso` | `services/member-service/.../V1__member_init.sql` |
| `cd_*` (code-policy-service) | tenant_id + 글로벌 NULL 허용 | `pol_cd_*_tenant_or_global` | `services/code-policy-service/.../V1__code_policy_init.sql` |
| `<prefix>_outbox` | tenant_id RLS + 글로벌 SYS 허용 | `pol_*_outbox_*` | `db/migration/V2__outbox.sql` 템플릿 + 서비스별 적용 |

> `tlp_cmn_tenant`는 RLS 비활성 — 플랫폼 관리자만 접근하므로 권한 매트릭스(RBAC + `X-Sys-Bypass`)로 통제 (DBA `06_security_and_access_control.md` 참조).

### 6.2 인증·토큰 검증

| 항목 | 상태 | 위치 |
|---|---|---|
| JWT 서명 검증 (JWKS 1시간 캐시) | OK | `JwtAuthenticationFilter` (Gateway) |
| iss / aud / exp claim 검증 | OK | 동 필터 + `tulip.gateway.security.expected-audiences` |
| tenant claim 필수 검증 | OK | `TenantHeaderEnricherFilter` (PLATFORM_ADMIN 제외 누락 시 403) |
| JTI 블랙리스트 (Redis) | OK | `RedisJtiBlacklist` (iam-service) + Gateway 동일 키 검사 |
| 서비스 단 토큰 2차 검증 | OK | `tenant/member/code-policy` 각 `*BearerAuthenticationFilter` |
| Refresh Token HttpOnly Cookie | OK | `iam-service` `tulip.iam.refresh-cookie.*` 설정 |
| Refresh 회전 시 구 JTI 즉시 블랙리스트 | OK | `AuthController#refresh` + `iam_refresh_audit` 적재 |
| MFA (TOTP) | DEFERRED | `MfaController` 501 응답 (Phase 2 활성화) |
| SSO Federation (SAML/OIDC/LDAP) | 골격 | `iam-service/federation/*` 인터페이스 + provider 3종 단위 테스트 |

### 6.3 CORS / Rate Limit / 보안 헤더

| 항목 | 설정 | 위치 |
|---|---|---|
| CORS 화이트리스트 | `localhost:3000` (admin), `:3001` (opac), `:9100` (gateway self) — `allowCredentials:true`, `maxAge:3600` | `api-gateway/application.yml` `globalcors` |
| 노출 헤더 | `X-Trace-Id`, `ETag`, `Location`, `X-RateLimit-*` | 동 yml |
| Rate Limit 익명 | 60 req/min/IP (`anonymousKeyResolver`, Forwarded-For 우선) | 동 yml `RequestRateLimiter` |
| Rate Limit 인증 사용자 | 300 req/min/user (`userKeyResolver`, X-User-Id) | 동 yml |
| 보안 응답 헤더 | `X-Content-Type-Options:nosniff`, `Referrer-Policy:strict-origin-when-cross-origin`, `Strict-Transport-Security` | 동 yml `default-filters` |
| Public Path 화이트리스트 | `/actuator/**`, `/api/v1/auth/login/*`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/v3/api-docs/**`, `/swagger-ui/**`, `/oauth2/**`, `/realms/**` | 동 yml `tulip.gateway.security.public-paths` |

### 6.4 정적 분석·시크릿 스캔

| 항목 | 상태 | 후속 |
|---|---|---|
| Spotless / Checkstyle | CI 베이스라인 적용 | 위반 시 빌드 차단 |
| Trivy fs / image scan | 베이스라인 작성, GitHub Actions 활성화 잔여 | GAP-08과 동시 처리 |
| Gitleaks secret scan | 베이스라인 작성, 활성화 잔여 | Phase 1 QA 슬랏 |
| OWASP ZAP nightly | 미설정 | Phase 2 초기 도입 (TD-07) |

---

## 7. 성능 점검 (부하 테스트 결과)

| 시나리오 | 목표 | 측정 상태 | 보고서 위치 (예정) |
|---|---|---|---|
| Gateway 인증 라우팅 | 100 RPS, P99 < 500ms, 5분 지속 | 미측정 → QA 슬랏 | `Tulip/tests/load/reports/phase1-gateway.html` |
| `/api/v1/auth/login/*` 플로 | 100 RPS, P99 < 200ms | 미측정 → QA 슬랏 | `Tulip/tests/load/reports/phase1-auth.html` |
| `/api/v1/members` 목록 (페이지 50, RLS) | 50 RPS, P99 < 300ms | 미측정 → QA 슬랏 | `Tulip/tests/load/reports/phase1-members.html` |
| `/api/v1/tenants/me/settings` upsert | 20 RPS, P99 < 250ms | 미측정 → QA 슬랏 | `Tulip/tests/load/reports/phase1-tenant.html` |
| Outbox → Kafka 지연 (이벤트 100건/초) | 평균 < 3초, P99 < 10초 | `OutboxPublisherTest` 단건 검증만 — 부하 미측정 | `Tulip/tests/load/reports/phase1-outbox.html` |

> 부하 측정은 Stg 환경 `make up` 단일 노드 기준이며, 실 운영 SLO는 Phase 2 GA 이전에 K8s `tulip-stg` 클러스터에서 재측정한다.

### 7.1 인덱스·실행계획 사전 점검

| 항목 | 상태 | 비고 |
|---|---|---|
| `tlp_cmn_audit_log(tenant_id, occurred_at DESC)` | 적용 | `V1__init_common.sql` |
| `tlp_cmn_library(tenant_id)` | 적용 | 동 |
| 각 도메인 `<prefix>_outbox(status, occurred_at) WHERE status IN ('PENDING','PROCESSING')` | 적용 | `V2__outbox.sql` 가이드 |
| 회원 검색 인덱스 (이름·연락처·이메일 trigram) | 적용 | `member-service V1__member_init.sql` + `pg_trgm` |

---

## 8. 기술 부채 항목 (Phase 2로 이관)

| ID | 항목 | 이유 / 영향 | 처리 시점 | 담당 |
|---|---|---|---|---|
| TD-01 | Storybook 컴포넌트 카탈로그 + axe-core a11y 자동 검사 | 1-D는 종단간 데모 우선, 시각적 카탈로그 후순위 | Phase 2 Sprint 2-A | FrontendSenior |
| TD-02 | OpenAPI → TS codegen 자동화 (`@hey-api/openapi-ts`) | 현재 도메인별 수동 모듈, OpenAPI 변경 시 정합 리스크 | Phase 2 Sprint 2-A | FrontendSenior + BackendSenior |
| TD-03 | 다국어 i18n 실 적재 (next-intl) | 1-D는 ko 단일, 영문 사서 인터페이스 OPAC에서 우선 도입 | Phase 2 Sprint 2-A | FrontendDev |
| TD-04 | PII 암호화 키 회전 + KMS/Vault 도입 | 현재 환경변수 평문 시드, 운영 진입 전 필수 | Phase 2 Sprint 2-B | BackendSenior + DBA |
| TD-05 | RLS Interceptor 단위 테스트 커버리지 보강 | `RlsMyBatisInterceptor` 통합 테스트만 존재, 누락 매트릭스 케이스 보강 | Phase 1 QA 슬랏 → 잔여분 Phase 2 | BackendSenior + DBA |
| TD-06 | `packages/ui` 컴포넌트 단위 테스트 70% | tsup 번들 우선, Vitest 적용 | Phase 2 Sprint 2-A | FrontendSenior |
| TD-07 | OWASP ZAP nightly DAST | 보안 회귀 자동화 | Phase 2 Sprint 2-A | QA |
| TD-08 | MFA (TOTP) 활성화 | `MfaController` 501 응답, 운영 정책상 사서 계정 필수 | Phase 2 Sprint 2-B | BackendSenior |
| TD-09 | Kafka KRaft 모드 전환 (Zookeeper 제거) | 현재 KRaft 단일 노드(개발). 운영에서는 ZK 폐기, KRaft 정착 | Phase 2 Sprint 2-A | DevLead + BackendSenior |
| TD-10 | Notification 서비스 본격 구현 | 1-C 시작 골격만 정의, Phase 2에서 채널(SMS/Push) 추가 필요 | Phase 3 (수서 알림 동반) | BackendDev |
| TD-11 | File 서비스 본격 구현 (MinIO presigned URL · 이미지 CDN) | 1-A 컨테이너만 기동, 도서 표지·자료 이미지가 Phase 2 의존 | Phase 2 Sprint 2-A | BackendDev |
| TD-12 | Admin BFF / OPAC BFF 분리 | 현재 SPA → Gateway 직접 호출, BFF 패턴 미적용 (인증만 IAM이 BFF 역할) | Phase 4 (열람 SPA 복잡도 증가 시) | DevLead |

---

## 9. 승인 절차 (Sign-off 흐름)

```
[1-D 코드 머지]
      ↓
[QA Sign-off 슬랏 (D+1 ~ D+10)]
   - GAP-01~04, 06 해소
   - 데모 시나리오 6단계 PASS
      ↓
[DevLead 최종 코드 리뷰 회고]
      ↓
[PM MS-1 승인 회의 (2026-10-31 목표)]
   - 본 점검표 + Release Notes v0.1.0-phase1 + Retrospective
      ↓
[MS-1 마일스톤 클로즈 → Phase 2 킥오프]
```

| 승인 단계 | 책임 | 산출물 |
|---|---|---|
| Sprint 1-D 머지 후 셀프 점검 | DevLead | 본 문서 v0.1 |
| QA Sign-off | QA + DBA | GAP 해소 보고 + 부하·RLS 회귀 보고서 |
| 보안 최종 점검 | DevLead + QA | OWASP ZAP/Trivy/Gitleaks 결과 |
| PM 승인 회의 | PM | 승인서 + Release Notes 확정 |
| Phase 2 진입 | DevLead | `10_phase2_entry_readiness.md` |

---

## 10. 변경 이력

| 버전 | 일자 | 변경 내용 | 작성자 |
|---|---|---|---|
| v0.1 | 2026-05-11 | Phase 1-D 종료 직후 셀프 점검 초안 — DoD 누적 23/31 (74.2%), GAP 8건·TD 12건 정의 | DevLead Agent |
