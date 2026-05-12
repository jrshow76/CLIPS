# Phase 2 진입 준비물 (Phase 2 Entry Readiness)

| 항목 | 내용 |
|---|---|
| 문서명 | Phase 2 "목록·장서" 진입 준비물 |
| 문서 ID | DEV-10 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | DevLead Agent |
| 검토자 | PM, Planner, BackendSenior, FrontendSenior, DBA, QA |
| 입력 | `04_dev_lead/09_phase1_exit_gate.md`, `01_pm/02_milestones_wbs.md` Phase 2 (§3.3), `04_dev_lead/02_service_decomposition.md`, `04_dev_lead/05_security_and_auth.md`, `10_dba/01_data_modeling_principles.md` |
| 후속 | `13_phase2_sprint_plan.md` (작성 예정) |
| 대상 기간 | 2026-11-01 ~ 2027-02-28 (4개월, MS-2) |
| 상태 | Phase 1 종료 게이트 직전 사전 준비 단계 |

---

## 1. 문서 목적

Phase 2 "목록·장서 GA(MS-2, 2027-02-28)" 진입 직전, **사전에 결정해야 할 기술 사항**과 **Phase 1 산출물을 어떻게 재사용할지**, 그리고 **신규로 통합해야 할 외부 인터페이스/라이브러리**를 정리한다. 본 문서는 Phase 2 킥오프 회의의 입력물이며, 미결 항목은 PM Risk Register에 등재한다.

---

## 2. Phase 2 범위 미리보기

`01_pm/02_milestones_wbs.md` §3.3에 따르면 Phase 2는 다음 10개 WBS로 분해된다.

| WBS ID | 작업 | 담당 | 기간 |
|---|---|---|---|
| 2.1 | KORMARC 데이터 모델·파서·편집기 | BackendSenior + DBA | 4w |
| 2.2 | MARC21 호환·변환 | BackendSenior | 2w |
| 2.3 | Z39.50 외부 검색·복사편목 | BackendSenior | 3w |
| 2.4 | 권위제어 (저자/주제) | BackendDev | 2w |
| 2.5 | 분류·청구기호·라벨 | BackendDev | 2w |
| 2.6 | 장서 등록·이관·폐기·점검 | BackendDev | 3w |
| 2.7 | 손망실·정정·재고 | BackendDev | 2w |
| 2.8 | UI: 편목 화면 (3pane 에디터) | FrontendSenior | 3w |
| 2.9 | UI: 장서 관리 화면 | FrontendDev | 2w |
| 2.10 | QA·통합 테스트 | QA | 2w |

> 본 문서는 1차로 **목록(catalog)** + **장서(collection)** 도메인을 다룬다. **수서(acquisition)·열람(circulation)·예약·연체·반납** 도메인은 Phase 3/4 진입 시 별도 readiness 문서로 작성하지만, 본 문서 §6 "테이블 미리보기"에서 Phase 1 인프라가 어떻게 받쳐줄지를 사전 정의한다.

### 2.1 Phase 2 데모 목표 (가설)

> "사서가 KORMARC 레코드를 직접 편집하거나 Z39.50 외부 검색으로 복사편목하여 자관 서지로 등록하고, 실물 자료를 입고·등록·라벨 출력하는 종단간 시연이 가능하다."

---

## 3. 추가될 서비스 모듈 목록

`02_service_decomposition.md`에서 정의된 16개 서비스 중 Phase 2에서 신규 구현되는 서비스는 다음과 같다.

| 서비스 | 포트(권장) | 책임 | Phase 1 의존 |
|---|---|---|---|
| **catalog-service** | 8105 | 서지(Bibliographic) 레코드, KORMARC/MARC21 모델, 권위제어, 분류 | iam, tenant, code-policy |
| **collection-service** | 8106 | 소장(Item) 레코드, 입고·이관·폐기·점검·손망실 | iam, tenant, member(검수자), catalog |
| **search-service** | 8107 | OpenSearch 색인 + Nori 분석기 + OPAC 통합 검색 + 패싯 | tenant, catalog, collection |
| **external-gateway** | 8108 | Z39.50 / SRU / KOLIS-NET / 국립중앙도서관 / 교보 / 알라딘 어댑터 | iam (서비스 토큰), code-policy |
| **file-service** | 8109 | MinIO presigned URL, 자료 이미지(표지·미리보기) + 라벨 출력 PDF | iam, tenant |
| **notification-service** (보강) | 8110 | 도서 입고 알림, 예약자 회신 — Phase 2 후반 | member, catalog |

> 옵션: `acquisition-service`(8111)는 Phase 3 본격, **희망도서 골격**만 Phase 2 후반 슬랏에서 catalog와 분리해 둔다.

### 3.1 모노레포 추가 위치

```
Tulip/backend/services/
├── catalog-service/         # 신규
├── collection-service/      # 신규
├── search-service/          # 신규
├── external-gateway/        # 신규
└── file-service/            # 신규 (MinIO presigned · 라벨 PDF)
```

`Tulip/backend/settings.gradle`에 위 5개 include 추가, 각 서비스 `build.gradle.kts`는 `common-core/web/security/tenant/data/test` 6종 의존 (Phase 1과 동일 패턴).

### 3.2 프론트엔드 추가 위치

```
Tulip/frontend/apps/admin/src/app/(shell)/
├── cataloging/              # 이미 placeholder 존재 → 본격 구현
│   ├── page.tsx             # 서지 검색·목록
│   ├── editor/[id]/page.tsx # 3-pane KORMARC 에디터
│   └── authority/page.tsx   # 권위 레코드 관리
└── collection/              # placeholder 존재 → 본격 구현
    ├── page.tsx             # 소장 목록·검색
    ├── intake/page.tsx      # 입고 처리
    └── inventory/page.tsx   # 점검·재고
```

> Phase 1-D에서 `(shell)/cataloging/page.tsx`, `(shell)/collection/page.tsx`가 placeholder로 존재 — `DomainPlaceholder` 컴포넌트로 안내만 렌더 (`apps/admin/src/app/(shell)/_components/DomainPlaceholder.tsx`).

---

## 4. 외부 인터페이스 카탈로그

### 4.1 표준 인터페이스

| 인터페이스 | 표준 | Phase 2 적용 | 비고 |
|---|---|---|---|
| **KORMARC** (한국문헌자동화목록) | KS X 6006-X | catalog-service 핵심 모델 | DBA `04_kormarc_schema.md` 결정 (예정) — 정형 컬럼 + JSONB 하이브리드 |
| **MARC21** | LoC | catalog-service 변환 어댑터 | 입출력 변환, KORMARC와 필드 매핑 테이블 필수 |
| **MODS** (선택) | LoC | search-service 색인 | OPAC 검색 응답 후순위 |
| **Dublin Core** | DCMI | external-gateway 응답 정규화 | 표준화 어댑터 |
| **ISBN-13 / ISSN** | ISO 2108 / 3297 | catalog-service 검증 | check digit 검증, 하이픈 정규화 |
| **Z39.50** | ANSI/NISO Z39.50 | external-gateway | 국립중앙·대학 도서관 복사편목 |
| **SRU / SRW** | LoC | external-gateway | XML 응답, HTTPS 권장 |
| **KDC** (한국십진분류법) | 6판 | code-policy-service 시드 (Phase 1) → catalog 사용 | 분류 입력 보조 |
| **DDC** (Dewey) | 23판 | 동 | 라이센스 검토 필요 (TD-Phase2-01) |
| **EAN-13** (바코드) | GS1 | collection-service 라벨 출력 | 청구기호 + 등록번호 라벨 |
| **RFID** (선택, Phase 5에서 본격) | ISO 28560 | collection-service 인터페이스 골격 | RFID 태그 인코딩 표준 |

### 4.2 외부 도서 데이터 API

| 제공자 | 엔드포인트 | 인증 | 응답 | 우선순위 |
|---|---|---|---|---|
| **국립중앙도서관 검색 API (서지검색)** | `https://www.nl.go.kr/NL/search/openApi/search.do` | API Key | XML/JSON | A (1차 도입) |
| **국립중앙도서관 SRU** | `http://nl.go.kr/sru` | 미인증 | SRU XML | A |
| **KOLIS-NET** | `https://www.kolisnet.or.kr/openapi/...` | 기관 인증 + API Key | XML | A (정식 인증은 Phase 6) |
| **교보문고 도서 검색** | `https://www.kyobobook.co.kr/openapi/...` | API Key | JSON | B (옵션) |
| **알라딘 OpenAPI** | `http://www.aladin.co.kr/ttb/api/...` | TTB Key | XML/JSON | B (옵션) |
| **Google Books API** | `https://www.googleapis.com/books/v1/...` | API Key | JSON | C (영문 보조) |
| **OpenLibrary** | `https://openlibrary.org/api/books` | 미인증 | JSON | C |
| **DOI / CrossRef** | `https://api.crossref.org/works/{doi}` | 미인증 | JSON | C (학술 자료) |

> Phase 2에서는 A 등급 3개를 우선 통합한다. external-gateway에서 각 어댑터를 `FederationProvider` 패턴(iam-service federation SPI 참조)으로 추상화하여 신규 제공자 추가가 손쉽도록 설계한다.

### 4.3 자료 이미지 / 표지 CDN

| 옵션 | 평가 | Phase 2 채택 |
|---|---|---|
| **MinIO + 자체 캐시** | 1-A에서 컨테이너 기동 완료, presigned URL 표준 | **채택 (1차)** |
| AWS S3 + CloudFront | 운영 진입 시 대안 | Phase 4 운영 검토 |
| 알라딘 / 교보 표지 URL 직접 노출 | 저작권 리스크 | 미채택 |
| 국립중앙도서관 표지 API | 사용 가능, 저화질 | 보조 |

> Phase 2 file-service는 **MinIO presigned PUT/GET URL**을 발급하고, 외부 API에서 표지 이미지를 1회 수집해 MinIO에 캐싱하는 패턴을 채택.

### 4.4 어댑터 인터페이스 표준

Phase 1 `iam-service` Federation SPI(SAML/OIDC/LDAP)와 동일한 패턴을 적용한다.

```
external-gateway/
└── src/main/java/com/tulip/external/
    ├── api/                               # REST 컨트롤러
    │   ├── BibSearchController.java
    │   └── CopyCatalogingController.java
    ├── provider/                          # SPI
    │   ├── BibProvider.java               # 인터페이스
    │   ├── KolisNetBibProvider.java
    │   ├── NlSearchBibProvider.java
    │   ├── KyoboBibProvider.java
    │   ├── AladinBibProvider.java
    │   └── Z3950BibProvider.java
    ├── registry/                          # Phase 1과 동일 패턴
    │   └── BibProviderRegistry.java
    ├── adapter/
    │   ├── KormarcMarc21Converter.java
    │   └── DublinCoreNormalizer.java
    └── resilience/                        # Resilience4j
        └── ExternalApiCircuitBreaker.java
```

---

## 5. 사전 결정 필요 기술 사항 (8건)

본 표는 Phase 2 킥오프 전에 **DevLead 단독 또는 협의 후 확정**되어야 할 항목이다. 미결 시 Sprint 2-A에서 PoC가 선행된다.

| ID | 결정 사항 | 옵션 | 권고 | 결정자 | 마감 |
|---|---|---|---|---|---|
| **DEC-01** | 검색 엔진 | OpenSearch 2.x (Phase 0 채택 ADR-015) vs Elasticsearch 8 | **OpenSearch 2.x 유지** — `docker-compose.yml`에 이미 컨테이너 정의, nori 한국어 분석기 정식 지원, Apache 2.0 라이센스. Elasticsearch SSPL은 SaaS 라이센스 리스크 | DevLead | Phase 2 D-7 |
| **DEC-02** | KORMARC 처리 라이브러리 | (a) MARC4J + 커스텀 KORMARC 확장 (b) 자체 파서 (c) 한국교육학술정보원 KERIS 라이브러리 | **(a) MARC4J 5.x + 커스텀 KORMARC 어댑터** — MARC21/KORMARC 공통 처리, leader 24바이트·directory·subfield 파싱 표준화. KS X 6006-X 한국 특수 필드는 어댑터에서 매핑. 단, PoC 1주 선행 필수 | BackendSenior + DBA | Phase 2 D-10 |
| **DEC-03** | KORMARC 저장 모델 | (a) 완전 정형 (필드별 컬럼) (b) 완전 JSONB (c) **하이브리드** (검색 필드는 정형, 원본은 JSONB) | **(c) 하이브리드** — `01_pm` 헌장 §5.4, DBA `01_data_modeling_principles.md` §2.3과 정합. 검색 빈도 높은 245$a/100$a/020$a/082$a는 별도 컬럼 + GIN/trigram, 원본 leader+directory+subfields는 `marc_record JSONB` | DBA + BackendSenior | Phase 2 D-14 |
| **DEC-04** | 파일 저장소 정착 | MinIO 단일 vs MinIO + 외부 S3 호환 | **MinIO 단일 정착 (Phase 2)**, Phase 4 운영 진입 시 S3/CloudFront 검토. Bucket 명명: `tulip-<tenant_code>-<domain>` (`tulip-demo1-cover`, `tulip-demo1-label`) | DevLead | Phase 2 D-3 |
| **DEC-05** | Z39.50 클라이언트 라이브러리 | (a) JZKit (Java) (b) yaz4j (yaz 바인딩) (c) 자체 BER 구현 | **(b) yaz4j** — `yaz` C 라이브러리 안정성, 다수 도서관 호환. Docker 이미지에 yaz 패키지 포함 필수 | BackendSenior | Phase 2 D-10 |
| **DEC-06** | 바코드·라벨 PDF 생성 | (a) iText 7 (AGPL/상용) (b) Apache PDFBox + ZXing (c) JasperReports | **(b) PDFBox 3.x + ZXing 3.x** — Apache 2.0, EAN-13 바코드 + 청구기호 라벨 충분. JasperReports는 통계 리포트(Phase 6)에서 재검토 | BackendDev | Phase 2 D-7 |
| **DEC-07** | OPAC 검색 UX 패턴 | (a) 즉시 검색 (CSR debounce) (b) 서버 검색(SSR) (c) **하이브리드** (SSR 초기, 패싯은 CSR) | **(c) 하이브리드** — Next.js 15 Server Component로 초기 결과 SSR(SEO), 패싯 변경은 nuqs URL 상태 + CSR fetch | FrontendSenior | Phase 2 D-7 |
| **DEC-08** | 권위 레코드 모델 | (a) 별도 authority 테이블 + 서지 FK (b) 서지 임베디드 + 비정규화 | **(a) 별도 authority 테이블** — 저자·주제명 표준화, 추후 KOLIS-NET 권위 데이터 import 시 호환 | DBA + BackendSenior | Phase 2 D-14 |

---

## 6. Phase 1 산출물 활용 매트릭스

Phase 2 신규 서비스가 **Phase 1 공통기반을 어떻게 재사용**하는지 명시한다. 이는 신규 서비스 개발자가 "어디서부터 새로 만들고, 어디까지 이미 있는지"를 즉시 알 수 있게 한다.

### 6.1 공통 라이브러리 재사용

| Phase 1 모듈 | Phase 2 활용 | 재사용 패턴 |
|---|---|---|
| `common-core` | 모든 신규 서비스 | `ApiResponse<T>`, `ErrorCode`, `TulipException`, `Pagination`, `TraceId` |
| `common-web` | 모든 신규 서비스 | `GlobalExceptionHandler`, `TraceIdFilter`, OpenAPI 공통 설정 |
| `common-security` | 모든 신규 서비스 | `JwtTokenProvider`, `TulipUserPrincipal`, `*BearerAuthenticationFilter` 패턴 |
| `common-tenant` | catalog/collection/search/file | `TenantContext`, `TenantContextFilter`, `@RequiresTenant` |
| `common-data` | catalog/collection/search/file | MyBatis 설정, `RlsMyBatisInterceptor`, `JsonbTypeHandler`, `UlidTypeHandler`, `pgcrypto TypeHandler` |
| `common-test` | 모든 신규 서비스 | Testcontainers PG/Redis/Kafka 헬퍼, TenantContextFixture |

### 6.2 인증·테넌트 컨텍스트 재사용

| Phase 1 산출물 | Phase 2 적용 방법 |
|---|---|
| Gateway `JwtAuthenticationFilter` | 라우팅 추가만 — `application.yml` `routes:`에 `catalog-service:8105` 등 5개 추가 |
| Gateway `TenantHeaderEnricherFilter` | 무수정 — 모든 다운스트림 서비스에 동일 헤더 전파 |
| iam-service `RedisJtiBlacklist` | 무수정 — Gateway가 Redis 키 검사 |
| `*BearerAuthenticationFilter` 패턴 (member/tenant/code-policy) | catalog/collection/search/file/external-gateway 각각 동일 패턴 복제 |
| `iam_user_link` 매핑 테이블 | 사서 계정 = Phase 1 계정 그대로 — 신규 가입 절차 없음 |
| Federation SPI | external-gateway에서 KOLIS-NET 인증 토큰 발급 시 재사용 (서비스 계정 모드) |

### 6.3 이벤트 토픽 명명 규칙 (Phase 1 표준 준수)

Phase 1에서 정착된 명명 규칙: `tulip.<service>.<aggregate>.<event>` (Kafka 키: `aggregateId` = ULID).

| 신규 토픽 | 발행자 | 구독자 | 비고 |
|---|---|---|---|
| `tulip.catalog.bib.created` | catalog-service | search-service, collection-service | 신규 서지 등록 |
| `tulip.catalog.bib.updated` | catalog-service | search-service | 서지 변경 → 색인 갱신 |
| `tulip.catalog.bib.deleted` | catalog-service | search-service, collection-service | 서지 삭제 |
| `tulip.catalog.authority.changed` | catalog-service | catalog-service(자기), search-service | 권위 변경 → 연관 서지 재색인 트리거 |
| `tulip.collection.item.created` | collection-service | search-service, notification-service | 입고 완료 → 예약자 알림 |
| `tulip.collection.item.status.changed` | collection-service | search-service | 폐기/이관/손망실 |
| `tulip.external.copy_cataloging.fetched` | external-gateway | catalog-service | 복사편목 결과 도착 |
| `tulip.search.index.failed` | search-service | (Sentry) | DLQ 패턴 |

### 6.4 DB 스키마·RLS 표준 재사용

| Phase 1 패턴 | Phase 2 적용 |
|---|---|
| 단일 DB(`tulip`) + 스키마 분리 (ADR-018) | 신규 스키마: `catalog`, `collection`, `search`, `file`, `external` |
| 명명 규칙: 도메인 prefix(`tnt_/mbr_/cd_`) | 신규 prefix: `cat_`, `col_`, `srh_`, `fil_`, `ext_` |
| 공통 컬럼 6종: `tenant_id, created_at, created_by, updated_at, updated_by, deleted_at, version` | 무수정 적용 |
| RLS 정책 `pol_<prefix>_<table>_tenant_iso` | 무수정 적용 |
| Outbox 테이블 `<prefix>_outbox` | 무수정 적용 (V2 템플릿) |
| Audit 로그 `tlp_cmn_audit_log` (공통) | 무수정 — service 컬럼만 변경 |

### 6.5 프론트엔드 공통 패키지 재사용

| Phase 1 패키지 | Phase 2 활용 |
|---|---|
| `@tulip/design-tokens` | 무수정 |
| `@tulip/ui` | `DataTable`, `PageHeader`, `ConfirmDialog`, `EmptyState`, `AccessDenied`, `AppSidebar`, `AppHeader` 무수정 재사용. 신규: `MarcEditor`(3-pane), `BibPreviewCard`, `LabelPrintPreview` |
| `@tulip/auth` | 무수정 |
| `@tulip/api-client` | 신규 도메인 모듈 추가: `bibs.ts`, `items.ts`, `authorities.ts`, `external.ts`, `files.ts` |
| `@tulip/config` | 신규 도메인 enum 추가 (BibStatus, ItemStatus, AcqStatus 등) |

---

## 7. Phase 2/3/4 도메인 미리보기 (선행 결정 필요 항목)

> 본 §은 Phase 2를 넘어 Phase 3(수서)·Phase 4(열람)에서 Phase 1·2 기반에 의존하는 부분을 사전에 식별해 둔다. Phase 2 진입 시점에 의사결정의 일관성을 유지하기 위함이다.

| 도메인 | Phase 2에서 미리 준비할 사항 |
|---|---|
| **수서 (Phase 3)** | catalog의 서지 자동 등록 훅(`tulip.acquisition.intake.completed` → catalog가 서지 생성) 인터페이스 사전 합의. 예산·회계연도 모델은 code-policy-service Policy 모델 재사용 |
| **대출/반납 (Phase 4)** | collection-service의 `item.status`에 `AVAILABLE/CHECKED_OUT/RESERVED/LOST/WITHDRAWN` 상태 머신 사전 정의. 동시성: 대출은 `SELECT ... FOR UPDATE` + `item.version` 낙관적 잠금 동시 사용. 핵심 인덱스 `cat_item(barcode)` UNIQUE + `(tenant_id, status, due_date)` 예측 |
| **예약 (Phase 4)** | catalog/collection 이벤트 구독 모델 사전 합의 — `tulip.collection.item.created`/`status.changed`/`due.imminent` → 예약 우선순위 큐 활성화 |
| **연체 (Phase 4)** | Phase 1 Spring Batch 인프라(`infra/batch`)에 야간 연체 계산 잡 자리표시자 — Policy Engine의 `LOAN_OVERDUE_RULE`을 사용 |
| **상호대차 (Phase 4)** | tenant-service의 `branches` 모델 + collection-service의 `item.location` 조합으로 분관 간 이동 기록 가능하게 사전 정의 |

---

## 8. 위험 사항 (Risk Register 보강 항목)

| ID | 위험 | 가능성 | 영향 | 완화 전략 |
|---|---|---|---|---|
| **R-P2-01** | 데이터 마이그레이션 — 기존 도서관 시스템(KOHA/Aleph/Symphony/한국산 등) 서지·소장 데이터 이관 | 高 | 高 | (1) 이관 도구 단위로 `migration-cli` 모듈 분리, (2) KORMARC export → 표준 MARCXML → catalog-service `/internal/migrations/bulk` 적재, (3) tenant별 dry-run 모드, (4) Phase 4 파일럿 직전 12주 슬랏 확보 (PM Risk Register에 R-13으로 별도 등재) |
| **R-P2-02** | 대규모 서지·소장 검색 성능 (1억건 시뮬레이션 시 P99) | 中 | 高 | (1) OpenSearch 인덱스 shard 설계 (tenant_id routing key), (2) GIN 인덱스 + Nori 분석기 한글 형태소, (3) 페이지네이션은 search_after 커서 강제, (4) DBA Sprint 2-B에 부하 테스트 매트릭스 1억건 정의 |
| **R-P2-03** | 대출·예약 race condition | 中 | 高 | (1) item 행 `SELECT ... FOR UPDATE` + version, (2) 예약 큐는 Redis Sorted Set + 단일 워커, (3) Phase 4 진입 직전 동시성 테스트 슬랏 명시 |
| **R-P2-04** | Z39.50 외부 서버 불안정 | 高 | 中 | Resilience4j 서킷 브레이커 (`@CircuitBreaker(name="z3950")`), 타임아웃 5초, fallback empty result + 사용자 안내 |
| **R-P2-05** | KORMARC 필드 매핑 누락 (한국 특수 필드 049 소장, 056 KDC, 052 KDC 청구기호) | 中 | 中 | DBA 사전 매핑 테이블 + 단위 테스트 (KORMARC ↔ MARC21 round-trip 1,000건 fixture) |
| **R-P2-06** | KOLIS-NET API Rate Limit | 高 | 中 | external-gateway에 일일/분당 한도 카운터, Redis 카운터 키 `ext:ratelimit:kolisnet:{tenant_id}` |
| **R-P2-07** | DDC 분류 데이터 라이센스 | 中 | 中 | OCLC 정식 라이센스 확인 — 미확보 시 KDC 단독 + DDC 입력 필드만 제공 |
| **R-P2-08** | DB 분리 시점 — 카탈로그가 폭증할 경우 catalog 전용 DB 분리 | 中 | 中 | Phase 4 진입 직전 DBA 평가. 현재는 ADR-018에 따라 단일 DB + 스키마 분리 유지 |
| **R-P2-09** | RFID 인터페이스 표준 분기 (ISO 28560 vs 미국식 LIB-RFID) | 低 | 中 | Phase 5 본격, Phase 2에는 골격만 — 미결로 두고 Phase 5 진입 시 결정 |
| **R-P2-10** | 외부 API 키 노출 | 中 | 高 | Vault PoC (TD-04와 동시 진행), `.env` 평문 키 운영 절대 금지 — Phase 2 Sprint 2-A에 명시 |

---

## 9. Phase 2 진입 체크리스트 (D-30 ~ D+0)

| D-시점 | 항목 | 책임 | 산출물 |
|---|---|---|---|
| D-30 | Phase 1 Retrospective | PM + 전 팀 | 회고록 + 액션아이템 |
| D-25 | DEC-01 ~ DEC-08 의사결정 회의 | DevLead + BackendSenior + DBA + FrontendSenior | 결정서 (본 문서 §5 갱신) |
| D-20 | KORMARC 전문가 컨설팅 일정 | PM + Planner | 일정 확정 + 워크숍 자료 |
| D-15 | MARC4J / yaz4j / PDFBox PoC | BackendSenior + BackendDev | PoC 코드 + 평가서 |
| D-14 | catalog/collection DDL 초안 | DBA | `services/*/db/migration/V1__*.sql` PR |
| D-10 | external-gateway provider 어댑터 3종 PoC | BackendSenior | KOLIS-NET / NL-API / Z39.50 각 1건 검색 성공 |
| D-7 | Phase 2 Sprint Plan 작성 (`13_phase2_sprint_plan.md`) | DevLead | 스프린트 분해 + DoD |
| D-5 | OpenSearch 매핑 설계 (한국어 + 다국어) | BackendSenior + DBA | `search-service/src/main/resources/index/bib-mapping.json` |
| D-3 | Phase 2 킥오프 자료 | PM | 발표 자료 |
| D+0 | Phase 2 킥오프 회의 | 전 팀 | 킥오프 회의록 + 백로그 확정 |

---

## 10. 변경 이력

| 버전 | 일자 | 변경 내용 | 작성자 |
|---|---|---|---|
| v0.1 | 2026-05-11 | Phase 2 진입 사전 준비 초안 — 서비스 5종, 외부 IF 카탈로그, 결정 필요 사항 8건, 위험 10건 정의 | DevLead Agent |
