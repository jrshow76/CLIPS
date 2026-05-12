# Tulip+ v0.1.0-phase1 릴리스 노트

| 항목 | 내용 |
|---|---|
| 버전 | v0.1.0-phase1 |
| 릴리스 일자 | 2026-05-12 |
| 마일스톤 | MS-1 (Phase 1 GA — 공통 기반) |
| 브랜치 | `claude/setup-tulip-library-4KPbi` |
| 빌드 상태 | Backend `gradle build` SUCCESSFUL · Frontend `pnpm build` 7/7 워크스페이스 SUCCESSFUL |

## 하이라이트

멀티테넌트 SaaS 형태의 도서관 통합관리시스템 Tulip+의 첫 데모 빌드. **인증·테넌트·라이브러리·회원·코드·정책 마스터 기능과 사서 대시보드/OPAC 스켈레톤이 한 사이클로 동작**한다. PostgreSQL Row-Level Security로 테넌트 데이터 누설을 차단하고, Outbox 패턴으로 도메인 이벤트를 Kafka로 신뢰성 있게 발행한다.

## 포함 기능

### 인프라
- Docker Compose 8서비스(PostgreSQL15·Redis7·Kafka KRaft·Keycloak24·MinIO·MailHog·Prometheus·Grafana)
- Gradle Multi-Project 백엔드 모노레포 + pnpm/Turborepo 프론트엔드 모노레포

### 공통 라이브러리(6종)
- `common-core` 표준 응답 envelope `ApiResponse<T>`, 에러 코드 체계(TLP-*), `Pagination`
- `common-web` GlobalExceptionHandler, TraceId 필터, RequestLogging 필터, OpenAPI
- `common-security` JWKS RS256 검증, JTI 블랙리스트, ABAC TenantAccessVoter, EntryPoint/AccessDenied 핸들러
- `common-tenant` TenantContext + TenantContextFilter + `@RequiresTenant`
- `common-data` BaseDomain, AuditingInterceptor, JSONB/ULID TypeHandler, RLS 컨텍스트 helper
- `common-test` Testcontainers·Fixture

### 백엔드 서비스
| 서비스 | 포트 | 엔드포인트 | 이벤트 토픽 |
|---|---:|---:|---:|
| api-gateway | 9100 | 라우팅 7종 + JWT/Tenant 필터 | — |
| iam-service | 8101 | 8(login initiate/callback/refresh/logout/me/introspect/mfa setup·verify 501) + Federation(SAML/OIDC/LDAP 스텁) | — |
| tenant-service | 8102 | 23(테넌트/라이브러리/분관/설정/내부) | `tulip.tenant.*` 8 |
| member-service | 8103 | 13(회원/카드/동의/me) | `tulip.member.*` 6 |
| code-policy-service | 8104 | 12(코드 그룹·값/정책/할당/효력/내부 캐시) | `tulip.code.*`, `tulip.policy.*` 6 |

### 데이터
- Flyway 마이그레이션 9개(common V1·V2, iam V1·V2, tenant V1, member V1, code-policy V1·V2)
- RLS 정책 72개(전 테넌트성 테이블에 FORCE RLS + SELECT/INSERT/UPDATE/DELETE 4종)
- 글로벌 시드 코드 5그룹·20값(MEMBER_TYPE/LIBRARY_TYPE/ITEM_TYPE/LOAN_STATUS/CONSENT_KIND)
- RLS 누설 회귀 테스트(2테넌트×5,000건 = 1만건) wrapper 스크립트

### 인증
- Keycloak realm `tulip` (admin-web/opac-web/iam-service 클라이언트, 6역할, tenant_id·branch_ids 프로토콜 매퍼)
- BFF 패턴 PKCE(state·verifier 서버 보관), Refresh HttpOnly 쿠키, Access 토큰 메모리 보관
- 401 single-flight 자동 갱신, JTI Redis 블랙리스트

### 프론트엔드
- 공통 패키지 7종: `design-tokens`, `ui`, `api-client`, `auth`, `config`, `tsconfig`, `eslint-config`
- UI 컴포넌트 30+: Atoms 9 · Molecules 14(KpiCard·ChartContainer·LineChartBlock·DonutChartBlock·BarChartBlock·ActivityFeed·AlertPanel·MetricMini 포함) · Organisms 6
- admin 앱 16라우트: 로그인·콜백·대시보드(KPI·차트·활동피드·알림·Top5) · 회원/카드/동의 · 도서관/분관 · 코드 관리
- opac 앱 8라우트: 메인·검색·상세·MyLibrary·로그인·콜백
- API 도메인 모듈 4: members/libraries/codes/tenants + dashboard·notifications + Mock 모드

### 품질
- Playwright E2E 5종(auth·members·libraries·rls·opac) + Page Object 5개 + 인증 픽스처
- k6 부하 스크립트 3종(auth 100 RPS · members 50 RPS · dashboard 30 RPS) + 공용 config
- RLS 누설 회귀 wrapper(`tests/rls/run-rls-tests.sh`)

## 변경 사항 (스프린트별 요약)

| 스프린트 | 핵심 산출 | 커밋 |
|---|---|---|
| Phase 0 | 기획·아키텍처·DB·디자인·QA·DBA 산출물 30+ | 다수 |
| 1-A | 모노레포/Docker Compose/공통 라이브러리 | `058c2f2` · `17f6f51` · `07d3430` |
| 1-B | Gateway + iam-service + 프론트 BFF 로그인 | `9d0b38c` · `cf33d96` |
| 1-C | 마스터 서비스 4종 + RLS + 관리 화면 | `a8490f3` · `91a70a1` |
| 1-D | 대시보드 풀 통합 + E2E + k6 + 운영 문서 | `94eddd6` + 후속 커밋 |

## 알려진 이슈 (Known Issues)

- 백엔드 실서비스에서 Direct Grant flow는 사용 금지(부하 테스트 한정)
- 대시보드 통계 전용 백엔드 엔드포인트 미구현 — 현재 mock 모드 또는 인접 API batch로 대체
- E2E·k6 자동 실행은 docker 가용 환경에서만 검증됨(CI에서 mock 모드 우선)
- 라이브러리 삭제 시 분관 존재 가드는 서비스 레벨에서만 처리(Phase 2에서 FK 제약 정렬)
- MFA·SSO Federation은 인터페이스/스텁만 준비(Phase 3 활성화)

## 다음 마일스톤

- **Phase 2 — 자료·소장·수서·대출 핵심 도메인** (예정: 2026-08-26 ~ 2026-12-15)
  - catalog-service / collection-service / acquisition-service / circulation-service
  - 외부 IF: KORMARC·MARC21 파서, 도서 정보 API, 검색 엔진(Elasticsearch/OpenSearch) 결정
- 자세한 진입 준비물은 `10_phase2_entry_readiness.md` 참조.
