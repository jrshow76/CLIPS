# Tulip+ Frontend Monorepo

도서관통합관리시스템 **Tulip+** 의 프론트엔드 모노레포다. pnpm workspace + Turborepo 기반으로
사서 관리자 앱(admin)과 이용자 OPAC 앱(opac)을 함께 관리한다.

> 본 단계는 **Phase 1-A 인프라 부트스트랩** 까지의 골격을 제공한다. 도메인 화면·실제 API
> 연동은 Phase 1-B 이후 Planner 정의서에 따라 추가된다.

---

## 디렉토리 구조

```
Tulip/frontend/
├─ package.json              # 루트 (pnpm + turbo)
├─ pnpm-workspace.yaml
├─ turbo.json
├─ tsconfig.base.json
├─ Makefile                  # 편의 명령
├─ packages/
│   ├─ design-tokens/        # 디자인 토큰 (TS / CSS variables / Tailwind preset)
│   ├─ ui/                   # 공통 컴포넌트 라이브러리 (atoms / molecules / organisms)
│   ├─ api-client/           # 공통 HTTP 클라이언트 + envelope + TanStack Query 팩토리
│   ├─ auth/                 # OAuth2 PKCE 클라이언트 (Keycloak 호환, mock 단계)
│   ├─ config/               # 환경설정·공통 상수·도메인 메타
│   ├─ tsconfig/             # 공유 TypeScript presets
│   └─ eslint-config/        # 공유 ESLint 설정
└─ apps/
    ├─ admin/                # 사서 관리자 (Next.js 15 App Router, 포트 3000)
    └─ opac/                 # 이용자 OPAC (Next.js 15 App Router, 포트 3001)
```

---

## 요구 환경

| 항목 | 버전 |
|---|---|
| Node | 20 LTS (`.nvmrc` 참고) |
| pnpm | 9.15+ |
| TypeScript | 5.5+ |
| OS | macOS / Linux 권장 (WSL2 가능) |

---

## 초기 설정

```bash
cd Tulip/frontend
pnpm install            # 모든 워크스페이스 의존성 설치
cp apps/admin/.env.example apps/admin/.env.local
cp apps/opac/.env.example apps/opac/.env.local
```

---

## 개발 명령

| 명령 | 설명 |
|---|---|
| `pnpm dev` (`make dev`) | admin + opac 동시 개발 (Turbo) |
| `pnpm --filter @tulip/admin dev` | admin만 (3000) |
| `pnpm --filter @tulip/opac dev` | opac만 (3001) |
| `pnpm build` | 전체 빌드 (packages → apps) |
| `pnpm lint` | 전체 ESLint |
| `pnpm typecheck` | 전체 TypeScript 검사 |
| `pnpm format` | Prettier 포매팅 |
| `pnpm clean` | 빌드 산출물 삭제 |

Makefile도 동일한 명령을 제공한다.

---

## 패키지 개요

### `@tulip/design-tokens`
DSN-02 / DSN-05 의 디자인 토큰을 코드화. `tokens.ts`, `tokens.css`, `tailwind-preset.ts` 3종을 제공하며
Light/Dark 두 테마를 `<html data-theme>` 으로 전환한다.

### `@tulip/ui`
shadcn/ui 컴포넌트 아이디어를 직접 코드 카피한 형태의 공통 라이브러리. 외부 헤드리스 의존을
최소화하기 위해 모달은 네이티브 `<dialog>` 를 사용한다.

- Atoms: Button, Input, Label, Badge, Icon, Spinner
- Molecules: FormField, SearchBar, Pagination, Toast(Provider 포함), Modal, DropdownMenu
- Organisms: AppHeader, AppSidebar, DataTable, PageHeader, EmptyState

### `@tulip/api-client`
ofetch 기반 `BaseClient` 와 표준 envelope(`ApiResponse<T>`) 타입을 제공. 인증 토큰, X-Tenant-Id,
X-Trace-Id(W3C traceparent), Idempotency-Key 헤더를 자동 첨부한다. TanStack Query hook 팩토리도
포함.

### `@tulip/auth`
OAuth2 Authorization Code + PKCE 흐름 클라이언트 (Keycloak 호환 URL). 본 단계는 인터페이스 +
mock 구현. Phase 1-B에서 실제 token endpoint 호출로 교체한다.

### `@tulip/config`
환경변수 검증(`zod`), 페이지네이션·헤더 상수, 6 도메인 메타데이터.

---

## 코드 컨벤션

- TypeScript strict, `noFallthroughCasesInSwitch`, `consistent-type-imports`.
- 컴포넌트: PascalCase, hook: `useXxx`, util: camelCase.
- 한글 주석 권장 (특히 도메인 의미가 있는 부분).
- shadcn/ui 기반 컴포넌트의 className 합성에는 `cn(clsx + twMerge)` 사용.
- 모든 인터랙티브 요소는 `focus-visible:shadow-focus` 포커스링을 유지한다.
- 디자인 토큰 → Tailwind 클래스 우선 (예: `bg-primary-500`, `text-neutral-900`).

---

## 후속 작업 (Phase 1-B ~)

- 실제 OAuth2 / Keycloak 토큰 교환
- OpenAPI 코드젠 (API 클라이언트 도메인 모듈 자동 생성)
- TanStack Query hooks 도메인별 정의
- Storybook 8 도입 (모든 Atom/Molecule)
- Playwright E2E (로그인·검색·대출·예약 스모크)
- axe-core 자동 a11y 회귀 테스트
- Pretendard 폰트 self-host

---

## 라이선스 / 책임

- 본 코드베이스는 Tulip+ 프로젝트 전용 (내부).
- 디자인·API·보안 표준 변경 시 PR 게이트에서 DevLead가 최종 검토한다.
