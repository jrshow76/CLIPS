# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 본 저장소에서 작업할 때 참고해야 할 가이드를 제공한다.

## 언어 규칙

모든 대화와 응답은 반드시 **한글**로 진행한다. 코드, 명령어, 고유명사를 제외한 모든 텍스트는 한글을 사용한다.

---

# 저장소 개요 (CLIPS)

`CLIPS`는 단일 코드베이스가 아닌, **여러 개의 독립 서비스/실험 프로젝트를 모아놓은 모노레포 형태의 워크스페이스**이다.
각 하위 디렉토리는 자체적인 기술 스택, 빌드 시스템, 도커 구성을 갖는 별도 프로젝트이며 서로 의존하지 않는다.

루트 트리:

```
CLIPS/
├── CLAUDE.md             # 본 문서 (워크스페이스 전역 가이드)
├── README.md             # 단순 안내 (`# CLIPS`)
├── .claude/agents/       # 10개 역할 기반 서브에이전트 정의
├── FootPrint/            # 장소 기록 서비스 (Spring Boot + Next.js)
├── Shelfy/               # 선반/구독 커머스 서비스 (Spring Boot + Next.js + MinIO)
├── photomosaic/          # 포토모자이크 생성기 (FastAPI + Vite + React)
└── sand-pixel/           # 단일 HTML 픽셀 실험 (정적 페이지)
```

작업을 시작하기 전 **어느 프로젝트의 작업인지** 먼저 확인하고, 해당 프로젝트의 디렉토리에서 명령을 실행한다.

---

# 프로젝트별 핵심 정보

## 1. FootPrint (`FootPrint/`)

장소 기록 / 통계 서비스. Supabase(또는 로컬 PostgreSQL)를 DB로 사용한다.

| 영역 | 기술 |
|---|---|
| Backend | Java 17, Spring Boot 3.3.0, Spring Security, Spring Data JPA, JJWT 0.12.5 |
| Frontend | Next.js 14 (App Router), React 18, TypeScript, TanStack Query v5, Zustand, react-hook-form + zod, Playwright |
| DB | PostgreSQL (Supabase) — 스키마 `footprint` |
| 외부 | 카카오 지도 API |

도메인 패키지(백엔드): `com.footprint.{auth,place,category,stats,common}` — 각 도메인은 `controller / service / repository / entity / dto` 5단 구조.

프론트엔드 디렉토리: `src/{app,components,lib,store,types}`.

실행:

```bash
cd FootPrint
cp .env.example .env        # DB_*, JWT_SECRET, KAKAO_MAP_KEY 채움

# 통합 실행
docker-compose up -d        # backend:8090, frontend:3002

# 개별 실행
cd backend && ./gradlew bootRun        # :8080
cd frontend && npm install && npm run dev   # :3000
npm run test:e2e            # Playwright
```

문서: `FootPrint/docs/`
- `architecture.md`, `dev_convention.md`, `project_plan.md`, `risk_register.md`
- `api/api_requirements.md`, `design/db_schema.md`
- `requirements/SRS.md`, `requirements/screen_definition.md`
- `test/test_cases.md`, `test/deployment_checklist.md`

## 2. Shelfy (`Shelfy/`)

"당신의 선반을 세상에 공개하세요" — 물품 등록·구매·구독 커머스 웹.

| 영역 | 기술 |
|---|---|
| Backend | Java 17, Spring Boot 3.3.0, Spring Security, JPA + **MyBatis 3.0.3**, JJWT, Flyway, MinIO SDK 8.5.10, Tika |
| Frontend | Next.js 14 (App Router), React 18, TypeScript, TanStack Query v5, Zustand, react-hook-form + zod, Tailwind CSS, lucide-react |
| DB | PostgreSQL 15 (Flyway 마이그레이션: `database/migrations/V1__init_schema.sql`, `V2__seed_data.sql`) |
| Storage | MinIO (개발용 S3 호환) — 버킷 `shelfy-images` |
| E2E | Playwright (`tests/auth|item|purchase|subscription.spec.ts`) — `baseURL=http://localhost:3000` |

도메인 패키지(백엔드): `com.shelfy.{auth,user,seller,item,order,subscription,file,security,config,common}` — `controller / service / repository(or mapper) / entity / dto(request|response)` 구조. **JPA와 MyBatis가 공존**하며, `seller`·`item`에는 MyBatis mapper가 별도로 존재한다.

프론트엔드 라우트(App Router): `(auth)/{login,signup}`, `browse`, `items/{new,[id]}`, `shelf/[userId]`, `mypage`, `dashboard`.

실행:

```bash
cd Shelfy
cp .env.example .env        # POSTGRES_*, JWT_SECRET, MINIO_*, MAIL_* 채움

# 통합 실행 (postgres + minio + minio-init + backend + frontend)
docker-compose up -d

# 개별 실행
cd backend && ./gradlew bootRun        # :8080
cd frontend && npm install && npm run dev   # :3000
npx playwright test         # tests/ — 백엔드+프론트 기동 상태 필요
```

서비스 URL: Frontend `:3000`, Backend `:8080/api/v1`, MinIO Console `:9001`, PostgreSQL `:5432`.

브랜치 전략(프로젝트 내부): `main` ← `develop` ← `feature/*` / `fix/*` / `hotfix/*`. PR은 DevLead 리뷰 후 `develop`으로 머지.

문서: `Shelfy/docs/{pm,planner,designer,devlead,dba,qa}/` — 역할별로 분리되어 있다. Designer 산출물은 `Shelfy/design/*.html`(퍼블리싱 결과)에 있고 컴포넌트화의 원본으로 사용한다.

## 3. photomosaic (`photomosaic/`)

이미지를 타일로 합성해 모자이크를 만드는 도구. Spring/Next 스택이 아닌 **Python + Vite**임에 유의.

| 영역 | 기술 |
|---|---|
| Backend | Python, FastAPI 0.115, Uvicorn, Pillow, NumPy, SciPy, APScheduler, slowapi (rate limit) |
| Frontend | Vite 5, React 18, TypeScript, TanStack Query v5, Zustand, axios |
| 저장소 | 로컬 파일시스템 (`/tmp/mosaic`) — DB 없음 |

백엔드 구조: `app/{api,services,models,core,utils}` + 진입점 `main.py`. API 라우터는 `/api/v1` prefix(`images`, `mosaic`, `sessions`). 만료 세션은 APScheduler가 1시간 주기로 정리한다.

프론트엔드 구조: `src/{components/{common,upload,gallery,mosaic},hooks,store,types,utils}`.

실행:

```bash
cd photomosaic
docker-compose up -d        # backend:8000, frontend:3000

# 개별 실행
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
cd frontend && npm install && npm run dev
```

환경변수: `BASE_UPLOAD_DIR`, `SESSION_TTL_SECONDS`, `MAX_CONCURRENT_JOBS`, `MAX_FILE_SIZE_MB`, `MAX_TOTAL_SIZE_MB`, `MAX_IMAGES_PER_SESSION`, `THUMBNAIL_SIZE` (docker-compose 기본값 참고).

`image.zip` 및 `result_*.jpg`는 샘플/결과물 데이터이므로 임의로 삭제하지 않는다.

## 4. sand-pixel (`sand-pixel/`)

단일 `index.html`로 구성된 클라이언트 전용 픽셀 아트 실험. 빌드 도구·서버 없음. 브라우저로 파일을 직접 열어 동작을 확인한다.

---

# 멀티 에이전트 협업 구조

이 워크스페이스는 **10개 역할 기반 서브에이전트**가 정의되어 있다(`.claude/agents/`).
사용자 요청 성격에 맞는 에이전트를 호출하여 작업을 위임한다.

## 에이전트 목록 및 호출 기준

| 에이전트 | 파일 | 호출 시점 |
|---|---|---|
| **PM** | `01_pm.md` | 일정·범위·리스크 관리, 배포 승인, 장애 에스컬레이션 |
| **Planner** | `02_planner.md` | 요구사항 분석, 기능 정의, 화면 흐름 설계, API 요구사항 정의 |
| **Designer** | `03_designer.md` | 화면 설계, 디자인 시스템 구성, 반응형 UI, HTML/CSS 퍼블리싱 |
| **DevLead** | `04_dev_lead.md` | 기술 아키텍처 설계, API 구조 수립, 코드 리뷰, 개발 표준 관리, 장애 대응 기술 총괄 |
| **BackendSenior** | `05_backend_senior.md` | 복잡한 API, 대량 데이터 처리, 외부 시스템 연동, Batch 처리, 성능 최적화 |
| **BackendDev** | `06_backend_dev.md` | 일반 REST API 개발, CRUD 구현, 기능 유지보수, 단순 Batch 개발 |
| **FrontendSenior** | `07_frontend_senior.md` | 공통 컴포넌트 개발, 상태관리 구조 설계, 대시보드·차트·에디터 등 복잡한 UI, 성능 최적화 |
| **FrontendDev** | `08_frontend_dev.md` | 입력 폼, 리스트·상세 화면, API 연동, UI 유지보수 및 버그 수정 |
| **QA** | `09_qa.md` | 테스트 시나리오 설계, 기능 테스트(수동/자동화), 버그 등록·추적, 배포 전 품질 최종 검증 |
| **DBA** | `10_dba.md` | SQL 튜닝, 실행계획 분석, 인덱스 설계, Lock/트랜잭션 병목 분석, HA 구성, DB 접근 권한 관리 |

## 협업 흐름

```
고객 요구사항
      ↓
  PM ←→ Planner
      ↓
  Designer ←→ Planner
      ↓
  DevLead
   ↙        ↘
BackendSenior  FrontendSenior
   ↓                ↓
BackendDev     FrontendDev
        ↘      ↙
          QA
          ↕
         DBA
```

### 요구사항 흐름
1. **PM → Planner**: 고객 요구사항 전달, 우선순위 확정
2. **Planner → DevLead**: API 요구사항 정의서, 기능 명세서 전달
3. **Planner → Designer**: 화면 정의서, 메뉴 구조도 전달
4. **DevLead → 개발자**: 업무 분배, 기술 가이드, 코드 리뷰

### 개발 흐름
1. **Designer → FrontendSenior**: HTML/CSS 퍼블리싱 결과물 전달 (Shelfy는 `Shelfy/design/*.html`)
2. **FrontendSenior**: React 컴포넌트 구조 설계, 공통 모듈 개발
3. **BackendSenior**: 핵심 API 개발, DBA 협의로 쿼리 최적화
4. **BackendDev / FrontendDev**: 가이드라인에 따라 기능 구현

### 품질 관리 흐름
1. **QA**: 기능 명세서 기반 테스트 케이스 작성 및 수행
2. **QA → DevLead**: 버그 우선순위 협의
3. **QA → PM**: 배포 전 QA 완료 보고
4. **PM**: QA 완료 보고서 확인 후 배포 승인

## 역할 경계 (충돌 방지)

| 업무 | 주도 | 협의 |
|---|---|---|
| SQL 최적화 | DBA | BackendSenior (쿼리 제공) |
| 인덱스 설계 | DBA | DevLead (방향 협의) |
| DB 권한 부여 실행 | DBA | DevLead (요청) |
| 공통 인증 구조 | DevLead (설계) → BackendSenior (구현) | — |
| 컴포넌트 구조 설계 | FrontendSenior | DevLead (기준 제시) |
| HTML/CSS 퍼블리싱 | Designer | — |
| React 컴포넌트화 | FrontendDev | FrontendSenior (가이드) |
| 장애 대응 (DB 계층) | DBA | DevLead (애플리케이션 계층) |

---

# 공통 기술 스택

워크스페이스 전반에서 권장되는 표준 스택. (photomosaic는 예외적으로 Python/Vite 사용)

- **Backend**: Java 17, Spring Boot 3.x, Spring Security, JPA / MyBatis, JJWT, Flyway
- **Frontend**: React 18, Next.js 14 (App Router), TypeScript 5, TanStack Query v5, Zustand, react-hook-form + zod, Tailwind CSS
- **Database**: PostgreSQL 15 (Shelfy는 Flyway, FootPrint는 Supabase)
- **Storage**: MinIO (개발) / S3 호환 (운영) — Shelfy 사용
- **Infra**: Docker, Docker Compose, GitHub Actions
- **API 테스트**: Postman, Newman
- **E2E 테스트**: Playwright (Shelfy `tests/`, FootPrint `frontend/tests/`)
- **협업 도구**: Git (PR 기반)

---

# 개발 원칙

- 모든 기능 구현은 PR 기반으로 진행하며 DevLead가 최종 리뷰한다.
- API 설계 규약(공통 요청/응답 포맷, 에러 코드)을 반드시 준수한다. 각 프로젝트의 `docs/devlead/dev-standards.md`(Shelfy) 또는 `docs/dev_convention.md`(FootPrint)를 우선 참고한다.
- 복잡한 쿼리 작성 전 DBA와 협의한다.
- 배포는 QA 완료 보고서 확인 후 PM이 승인한다.
- 복잡한 비즈니스 로직·쿼리는 BackendSenior, 일반 CRUD는 BackendDev가 담당한다.
- 디자이너가 제공한 HTML/CSS 구조를 FrontendDev가 최대한 유지하여 컴포넌트화한다.
- 도메인별 5단 구조(`controller / service / repository(or mapper) / entity / dto`)와 패키지 단위 모듈화 컨벤션을 따른다.
- `.env` 및 비밀키 파일은 절대 커밋하지 않는다. 신규 변수는 `.env.example`에 추가한다.

---

# 자주 쓰는 명령 요약

| 목적 | 디렉토리 | 명령 |
|---|---|---|
| Shelfy 전체 기동 | `Shelfy/` | `docker-compose up -d` |
| Shelfy 백엔드 단독 | `Shelfy/backend` | `./gradlew bootRun` |
| Shelfy 프론트 단독 | `Shelfy/frontend` | `npm install && npm run dev` |
| Shelfy 타입 체크 | `Shelfy/frontend` | `npm run type-check` |
| Shelfy E2E | `Shelfy/` | `npx playwright test` |
| FootPrint 전체 기동 | `FootPrint/` | `docker-compose up -d` (backend:8090, frontend:3002) |
| FootPrint 백엔드 단독 | `FootPrint/backend` | `./gradlew bootRun` |
| FootPrint E2E | `FootPrint/frontend` | `npm run test:e2e` |
| photomosaic 기동 | `photomosaic/` | `docker-compose up -d` (backend:8000, frontend:3000) |
| photomosaic 백엔드 단독 | `photomosaic/backend` | `uvicorn main:app --reload` |

UI 또는 프론트엔드 변경 시에는 위 dev 서버를 실제로 띄워 골든 패스와 엣지 케이스를 브라우저에서 확인한 뒤 작업 완료로 보고한다. 확인이 불가능하면 그 사실을 명시한다.
