# TradePilot Frontend

Next.js 14 (App Router) + TypeScript(strict) + Tailwind + TanStack Query v5 + Zustand 기반의
자동주식매매 프론트엔드.

## 빠른 시작

```bash
cd frontend
cp .env.local.example .env.local
npm install          # 또는 pnpm install / yarn
npm run dev          # http://localhost:3000
```

> 백엔드가 준비되지 않았다면 `.env.local`에서 `NEXT_PUBLIC_USE_MOCK=true`로 두세요.
> 데모 사용자(`김주식 / SIM 모드`)와 정적 데이터로 모든 화면이 동작합니다.

## 환경 변수

| 변수 | 설명 |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | 백엔드 base URL (없으면 same-origin `/api/v1` rewrite 사용) |
| `NEXT_PUBLIC_WS_BASE_URL` | WebSocket base URL |
| `NEXT_PUBLIC_USE_MOCK` | `true` 시 mock 데이터로 동작 |
| `NEXT_PUBLIC_APP_ENV` | development / staging / production |
| `NEXT_PUBLIC_TRACE_PREFIX` | 클라이언트 trace ID 접두사 |

## 디렉토리

```
src/
├── app/                 App Router (라우팅, layout, page)
│   ├── (auth)/          로그인/회원가입
│   └── (app)/           인증 필요 영역 (AppShell)
├── components/
│   ├── ui/              디자인 시스템 매핑 (BEM 1:1)
│   ├── charts/          lightweight-charts / Recharts 래퍼
│   └── layout/          AppShell, Header, Sidebar, LiveModeModal
├── lib/
│   ├── api/             axios 클라이언트, queries, query-keys
│   ├── auth/            세션 토큰 저장소
│   ├── constants/       라우트, 에러코드, staleTime
│   ├── mocks/           정적 mock 데이터
│   └── utils/           cn, format, date
├── providers/           Query/Theme/Auth 통합 Provider
├── stores/              Zustand (auth, trade-mode, theme, notification)
├── styles/              tokens.css, base.css, components.css (Designer 동기화)
└── types/               도메인 타입 정의
```

## 상태 관리

| 상태 | 도구 | 위치 |
|---|---|---|
| 서버 캐시 | TanStack Query | `lib/api/queries/*.ts` |
| 사용자 세션 | Zustand | `stores/auth-store.ts` |
| 매매 모드 | Zustand + persist | `stores/trade-mode-store.ts` |
| 테마 | Zustand + persist | `stores/theme-store.ts` |
| 토스트 큐 | Zustand | `stores/notification-store.ts` |

### TanStack Query 컨벤션

- 키: `['domain', 'action', ...params]` (단일 출처: `lib/api/query-keys.ts`)
- staleTime 기본값:
  - 시세 3초, 캔들 60초, 마스터 1시간
- mutation 성공 시 관련 query를 `queryClient.invalidateQueries`로 무효화

## 디자인 시스템

- **단일 출처**: `src/styles/tokens.css` (Designer 원본과 동일)
- **CSS 변수 → Tailwind**: `tailwind.config.ts`의 `theme.extend`에서 매핑.
  - 색상: `bg.0 ~ bg.4`, `fg.1 ~ fg.3`, `brand.50 ~ 900`, `up`, `down`, `success`, `warning`, `danger`, `info`, `mode.sim`, `mode.live`
  - 사이즈: `text-12 ~ text-40`, `spacing 1~16`
- **BEM 클래스** (`.btn`, `.card`, `.modal`, `.badge` 등)와 Tailwind 유틸은 충돌 없이 공존.
- 다크/라이트는 `data-theme` 속성으로 전환되며 `useThemeStore` 토글.

## API 클라이언트 인터셉터

`lib/api/client.ts`:
- `Authorization` 자동 부착 (세션 토큰 → `lib/auth/session.ts`)
- `X-Trade-Mode` 자동 주입 (요청 옵션 `requireTradeMode: true` 시)
- `X-Idempotency-Key` 자동 발급 (`idempotent: true` 시)
- `X-Request-Id` 자동 발급 (trace_id 연동)
- 401 + E0001 → refresh 토큰으로 1회 자동 재시도
- 표준 envelope 해석 → 실패 시 `AppError` throw

## LIVE 모드 보호

1. 헤더의 `TradeModeToggle.click('LIVE')` → store `liveConfirmOpen = true`
2. 전역에 마운트된 `LiveModeModal`이 열림 (`AppShell`에서 자동 마운트)
3. 사용자가 `"LIVE"` 텍스트를 정확히 입력해야 확인 버튼 활성화
4. 권한 검증 (`ROLE_TRADER_PRO` 이상) + `useSwitchTradeMode` mutation 호출
5. 성공 시 `setMode('LIVE', { confirmed: true })`로 모드 변경

직접 `setMode('LIVE')`를 호출하더라도 `confirmed:true` 없이는 모달이 다시 열리므로 우회 불가.

## 빌드 / Docker

```bash
npm run build                    # .next/standalone 생성
docker build -t tradepilot-frontend .
docker run -p 3000:3000 --env-file .env.local tradepilot-frontend
```

## FrontendDev 인계 포인트

1. **추천주 상세** `app/(app)/recommendations/[code]/page.tsx`: `useStockDetail` + `useCandles` + `IndicatorPanel` 조합으로 차트 페이지와 유사하게 구현.
2. **시그널 상세** `app/(app)/signals/[id]/page.tsx`: 시그널 본문 + 차트 미리보기 + "이 시그널로 주문" CTA (LIVE 시 2단계 확인 모달).
3. **전략 폼** `app/(app)/auto-trading/[id]/page.tsx`: `react-hook-form` + `zod` 사용. `useSaveStrategy` mutation에 그대로 연결.
4. **주문 모달**: `components/ui/modal.tsx`를 그대로 사용하고 LIVE 모드면 `danger` variant + 텍스트 확인 패턴 복제.
5. **WebSocket**: `lib/ws/` 디렉토리 추가 예정. `providers/Providers.tsx`에 `WsProvider` 합류.

## 코딩 규칙

- `client.ts`의 `apiRequest`는 직접 사용보다 도메인 query 훅 사용 권장.
- 새로운 도메인 query 작성 시:
  1. `types/<domain>.ts`에 타입 추가
  2. `lib/api/query-keys.ts`에 키 등록
  3. `lib/api/queries/<domain>.ts`에 hook + mock 분기 작성
  4. 컴포넌트에서 hook만 import (api 객체 직접 사용 지양)
- 모든 화면 텍스트는 **한글**, 등락은 상승=빨강 / 하락=파랑.
- 숫자 표기는 `formatCurrency` / `formatPct` / `formatPnl`을 사용해 일관 유지.
