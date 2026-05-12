# TradePilot 프론트엔드 디렉토리 구조 (Frontend Structure)

> 문서 ID: 22_FRONTEND_STRUCTURE
> 버전: v1.0
> 작성자: DevLead
> 최종 수정일: 2026-05-12

본 문서는 Next.js 14(App Router) + TypeScript 기반 프론트엔드의 디렉토리 구조, 라우팅 트리, 상태관리 전략을 정의한다.

---

## 1. 기술 스택 / 결정 사항

| 항목 | 채택 | 사유 |
|---|---|---|
| 프레임워크 | Next.js 14 (App Router) | 서버 컴포넌트(RSC), 라우트 핸들러, SSR/CSR 혼합 |
| 언어 | TypeScript 5.x (strict) | 타입 안전 |
| 스타일 | Tailwind CSS + CSS Variables | 디자인 토큰, 유틸리티 우선 |
| 서버 상태 | TanStack Query v5 | 캐시/리트라이/리프레시 일원화 |
| 클라이언트 상태 | Zustand | 작은 보일러플레이트, persist 미들웨어 |
| 폼 | React Hook Form + Zod | 검증 일원화 |
| 차트 | lightweight-charts (캔들) + Recharts (PnL 등 라인/막대) | 금융 차트와 일반 차트 분리 |
| HTTP | ky (or axios) | 인터셉터, 표준 응답 처리 |
| WS | native WebSocket + 재연결 래퍼 | TanStack Query 캐시 invalidation 연동 |
| 테이블 | TanStack Table v8 | 정렬/필터/페이지 |
| 아이콘 | lucide-react | - |
| 다크모드 | next-themes | 시스템 토글 |
| 테스트 | Vitest + Testing Library, Playwright | 단위/E2E |

---

## 2. 디렉토리 트리

```
frontend/
├── package.json
├── tsconfig.json
├── next.config.mjs
├── tailwind.config.ts
├── postcss.config.mjs
├── .eslintrc.cjs
├── .prettierrc
├── Dockerfile                       # FrontendSenior 작성 예정
├── public/
│   ├── favicon.ico
│   └── images/
└── src/
    ├── app/                         # App Router (라우팅)
    │   ├── layout.tsx               # 루트 레이아웃 (테마, providers)
    │   ├── globals.css
    │   ├── error.tsx
    │   ├── not-found.tsx
    │   ├── (auth)/
    │   │   ├── login/page.tsx
    │   │   ├── signup/page.tsx
    │   │   └── password-reset/page.tsx
    │   ├── (app)/                   # 인증 필요 영역
    │   │   ├── layout.tsx           # 헤더/사이드바, 모드 배지
    │   │   ├── dashboard/page.tsx
    │   │   ├── recommendations/
    │   │   │   ├── page.tsx
    │   │   │   └── [code]/page.tsx
    │   │   ├── charts/
    │   │   │   └── [code]/page.tsx
    │   │   ├── sectors/
    │   │   │   ├── page.tsx
    │   │   │   └── [code]/page.tsx
    │   │   ├── signals/
    │   │   │   ├── page.tsx
    │   │   │   └── [id]/page.tsx
    │   │   ├── strategies/
    │   │   │   ├── page.tsx
    │   │   │   ├── new/page.tsx
    │   │   │   └── [id]/page.tsx
    │   │   ├── orders/
    │   │   │   ├── page.tsx
    │   │   │   └── [id]/page.tsx
    │   │   ├── portfolios/page.tsx
    │   │   ├── backtest/
    │   │   │   ├── page.tsx
    │   │   │   ├── new/page.tsx
    │   │   │   └── [jobId]/page.tsx
    │   │   ├── reports/page.tsx
    │   │   ├── notifications/page.tsx
    │   │   └── settings/
    │   │       ├── trade-mode/page.tsx
    │   │       ├── risk-limits/page.tsx
    │   │       ├── schedules/page.tsx
    │   │       └── creon/page.tsx
    │   ├── (admin)/                 # ADMIN/OPERATOR
    │   │   ├── layout.tsx
    │   │   ├── users/page.tsx
    │   │   ├── audit-logs/page.tsx
    │   │   └── system/page.tsx
    │   └── api/                     # Next.js route handlers (BFF 최소)
    │       └── health/route.ts
    │
    ├── components/                  # UI 컴포넌트
    │   ├── ui/                      # 디자인 시스템 (Designer 정의)
    │   │   ├── button.tsx
    │   │   ├── input.tsx
    │   │   ├── select.tsx
    │   │   ├── dialog.tsx
    │   │   ├── table.tsx
    │   │   ├── badge.tsx
    │   │   ├── toast.tsx
    │   │   └── ...
    │   ├── layout/
    │   │   ├── header.tsx
    │   │   ├── sidebar.tsx
    │   │   ├── trade-mode-badge.tsx # SIM/LIVE 배지 (전역 가시)
    │   │   └── kill-switch-button.tsx
    │   ├── charts/
    │   │   ├── candle-chart.tsx     # lightweight-charts
    │   │   ├── indicator-overlay.tsx
    │   │   ├── pnl-line-chart.tsx   # Recharts
    │   │   ├── sector-heatmap.tsx
    │   │   └── compare-chart.tsx
    │   ├── domain/                  # 화면별 합성 컴포넌트
    │   │   ├── dashboard/
    │   │   │   ├── holdings-card.tsx
    │   │   │   ├── daily-pnl.tsx
    │   │   │   ├── market-summary.tsx
    │   │   │   └── reco-top5.tsx
    │   │   ├── recommendations/
    │   │   ├── signals/
    │   │   ├── orders/
    │   │   ├── strategies/
    │   │   ├── backtest/
    │   │   └── settings/
    │   └── feedback/
    │       ├── confirm-dialog.tsx   # 2단계 확인 UI
    │       └── error-boundary.tsx
    │
    ├── lib/                         # 무상태 유틸 / 인프라
    │   ├── api/
    │   │   ├── client.ts            # HTTP 클라이언트, 인터셉터
    │   │   ├── errors.ts            # 에러 코드 → 메시지 매핑
    │   │   ├── trade-mode.ts        # X-Trade-Mode 헤더 주입
    │   │   ├── idempotency.ts       # X-Idempotency-Key 생성
    │   │   └── endpoints/           # 도메인별 API 함수
    │   │       ├── auth.ts
    │   │       ├── stocks.ts
    │   │       ├── indicators.ts
    │   │       ├── orders.ts
    │   │       ├── signals.ts
    │   │       ├── strategies.ts
    │   │       ├── portfolios.ts
    │   │       ├── backtest.ts
    │   │       ├── ml.ts
    │   │       ├── settings.ts
    │   │       ├── reports.ts
    │   │       └── ...
    │   ├── ws/
    │   │   ├── client.ts            # WS 연결 + 재연결
    │   │   ├── channels.ts          # quotes/signals/notifications
    │   │   └── query-invalidator.ts # 이벤트 → TanStack Query 무효화
    │   ├── auth/
    │   │   ├── session.ts           # access/refresh 저장(httpOnly cookie 우선)
    │   │   └── permission.ts        # 역할 기반 가드
    │   ├── format/
    │   │   ├── number.ts            # 통화/퍼센트
    │   │   ├── date.ts              # KST/UTC 표시
    │   │   └── stock.ts             # 종목코드 검증
    │   ├── validation/
    │   │   └── schemas/             # Zod 스키마 (서버 검증과 동기)
    │   ├── theme/
    │   │   ├── tokens.ts
    │   │   └── provider.tsx
    │   └── const/
    │       ├── error-codes.ts
    │       └── trade-mode.ts
    │
    ├── hooks/                       # React 훅
    │   ├── queries/                 # TanStack Query 훅 (도메인별)
    │   │   ├── use-portfolio.ts
    │   │   ├── use-recommendations.ts
    │   │   ├── use-signals.ts
    │   │   ├── use-orders.ts
    │   │   ├── use-strategies.ts
    │   │   ├── use-backtest-job.ts
    │   │   └── use-ml-prediction.ts
    │   ├── mutations/
    │   │   ├── use-create-order.ts
    │   │   ├── use-switch-trade-mode.ts
    │   │   ├── use-kill-switch.ts
    │   │   └── use-save-strategy.ts
    │   ├── use-ws-channel.ts        # WS 구독 훅
    │   ├── use-trade-mode.ts        # 전역 모드 헬퍼
    │   ├── use-confirm.ts           # 2단계 확인 모달
    │   └── use-toast.ts
    │
    ├── stores/                      # Zustand 스토어 (UI/세션 상태)
    │   ├── auth-store.ts            # 로그인 사용자, 권한
    │   ├── trade-mode-store.ts      # 현재 SIM/LIVE (서버 값과 동기)
    │   ├── ui-store.ts              # 사이드바 토글, 테마
    │   ├── chart-store.ts           # 차트 도구 상태(지표 on/off)
    │   └── notification-store.ts    # 읽지 않은 알림 카운트
    │
    ├── types/                       # 도메인 타입 정의 (서버 응답 ↔ FE)
    │   ├── api.ts                   # 공통 Response/Page
    │   ├── auth.ts
    │   ├── stock.ts
    │   ├── signal.ts
    │   ├── strategy.ts
    │   ├── order.ts
    │   ├── portfolio.ts
    │   ├── backtest.ts
    │   ├── ml.ts
    │   └── setting.ts
    │
    ├── providers/                   # 컨텍스트 프로바이더 묶음
    │   ├── query-provider.tsx       # TanStack Query
    │   ├── theme-provider.tsx
    │   ├── auth-provider.tsx
    │   ├── toast-provider.tsx
    │   └── ws-provider.tsx          # 앱 단위 WS 연결
    │
    └── styles/
        └── tokens.css               # CSS 변수 (디자인 토큰)
```

---

## 3. 라우팅 트리 (App Router)

```
/
├── /login                           (auth)
├── /signup                          (auth)
├── /password-reset                  (auth)
├── /dashboard                       (app, default home)
├── /recommendations                 (app)
│   └── /recommendations/{code}      종목 상세
├── /charts/{code}                   (app)
├── /sectors                         (app)
│   └── /sectors/{code}              섹터 드릴다운
├── /signals                         (app)
│   └── /signals/{id}                시그널 상세
├── /strategies                      (app)
│   ├── /strategies/new
│   └── /strategies/{id}
├── /orders                          (app)
│   └── /orders/{id}                 주문 상세
├── /portfolios                      (app)
├── /backtest                        (app)
│   ├── /backtest/new
│   └── /backtest/{jobId}
├── /reports                         (app)
├── /notifications                   (app)
├── /settings/trade-mode             (app, 2-step 확인)
├── /settings/risk-limits            (app)
├── /settings/schedules              (app)
├── /settings/creon                  (app)
└── /admin/...                       (admin)
```

### 3.1 라우트 그룹
- `(auth)`: 비로그인 영역, 별도 레이아웃.
- `(app)`: 로그인 필수, 헤더/사이드바/모드 배지/KillSwitch 버튼 공통.
- `(admin)`: ADMIN/OPERATOR 전용, 좌측 메뉴 분리.

### 3.2 SSR / CSR / ISR 전략
| 페이지 | 렌더링 | 사유 |
|---|---|---|
| `/login`, `/signup` | SSR (정적) | SEO 불필요, 초기 페이지 빠름 |
| `/dashboard` | CSR (RSC + 클라이언트 컴포넌트 혼합) | 사용자 데이터, 실시간 |
| `/charts/[code]` | CSR | 차트 인터랙션 중심 |
| `/sectors`, `/recommendations` | SSR + 클라이언트 캐시 | 초기 데이터 prefetch 후 TanStack Query에 hydration |
| `/backtest/[jobId]` | CSR (polling) | 진행률 실시간 갱신 |

- **데이터 prefetch**: 서버 컴포넌트에서 `queryClient.prefetchQuery` 후 HydrationBoundary로 전달.

---

## 4. 상태관리 전략

### 4.1 책임 분리
| 상태 종류 | 도구 | 예시 |
|---|---|---|
| 서버 상태 (캐시/리트라이) | TanStack Query | 보유종목, 추천주, 주문 목록 |
| 클라이언트 UI 상태 | Zustand | 사이드바 open, 차트 지표 토글 |
| 세션 상태 | Zustand + httpOnly cookie | 로그인 사용자, 권한, 현재 모드 |
| 폼 상태 | React Hook Form | 전략 작성, 한도 설정 |
| URL 상태 | searchParams | 페이지/필터/정렬 |

### 4.2 TanStack Query 컨벤션
- **Query Key**: `['domain', 'action', ...params]` 배열. 예: `['orders', 'list', { status, page }]`.
- **staleTime**: 시세 3s, 캔들 60s, 마스터 데이터 1h.
- **mutations**: 성공 시 관련 Query 무효화 (`queryClient.invalidateQueries`).
- **WS 이벤트 처리**: 수신 즉시 `setQueryData` 또는 `invalidate`.

```ts
// hooks/queries/use-orders.ts
export const useOrders = (params: OrdersQuery) =>
  useQuery({
    queryKey: ['orders', 'list', params],
    queryFn: () => api.orders.list(params),
    staleTime: 5_000,
  });
```

### 4.3 Zustand 컨벤션
- 각 스토어는 단일 책임. 도메인 데이터를 영구 저장하지 않는다 (서버 상태와 충돌 방지).
- persist 미들웨어는 UI 설정(테마, 사이드바)에만 적용.

```ts
// stores/trade-mode-store.ts
type State = { mode: 'SIM' | 'LIVE'; setMode: (m: 'SIM' | 'LIVE') => void };
export const useTradeMode = create<State>((set) => ({
  mode: 'SIM',
  setMode: (mode) => set({ mode }),
}));
```

### 4.4 모드 (SIM/LIVE) 동기화
1. 로그인 직후 `/users/me`의 `trade_mode`를 Zustand에 저장.
2. `TradeModeBadge`는 Zustand 값을 구독하여 색상 표시 (SIM=파랑, LIVE=빨강).
3. `/orders` 호출 시 `lib/api/trade-mode.ts`가 `X-Trade-Mode` 헤더를 Zustand 값으로 자동 주입.
4. 모드 전환 mutation 성공 시 Zustand + `/users/me` Query 둘 다 갱신.

---

## 5. API 클라이언트 인터셉터

```ts
// lib/api/client.ts
export const api = ky.create({
  prefixUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
  timeout: 10_000,
  hooks: {
    beforeRequest: [attachAuthToken, attachTradeMode, attachIdempotencyKey],
    afterResponse: [unwrapResponse, refreshOn401, handleErrorCode],
  },
});
```

- `attachAuthToken`: access 토큰 헤더 부착.
- `attachTradeMode`: 주문/모드 분기 API에 `X-Trade-Mode` 자동 주입.
- `refreshOn401`: 401 + `E0001`이면 refresh → 1회 재시도.
- `handleErrorCode`: `success=false`면 `AppError` throw, toast 표시.

---

## 6. WebSocket 통합

```ts
// providers/ws-provider.tsx
useEffect(() => {
  const ws = openSocket('/ws/signals', token);
  ws.on('signal', (m) => queryClient.invalidateQueries({ queryKey: ['signals'] }));
  ws.on('order_update', (m) => queryClient.setQueryData(['orders', 'detail', m.id], m));
  return () => ws.close();
}, [token]);
```

- 채널: `/ws/quotes`, `/ws/signals`, `/ws/notifications`.
- 재연결: 지수 백오프, 토큰 만료 시 refresh 후 재연결.

---

## 7. 디자인 시스템 / 테마

- **토큰**: `styles/tokens.css`에 CSS 변수로 정의 (color, spacing, radius, shadow).
- **라이트/다크**: `data-theme` 속성 토글, `next-themes` 사용.
- **반응형 브레이크포인트**: `sm:640px / md:768px / lg:1024px / xl:1280px`.
- **접근성**: 모든 인터랙티브 요소 키보드 접근, ARIA 라벨, WCAG 2.1 AA.

---

## 8. 2단계 확인 UI 패턴

- 실거래 주문, 모드 전환, Kill Switch 등 위험 액션은 `<ConfirmDialog />`로 2단계 처리.
- 1단계: 의도 확인 + 변경 내용 요약.
- 2단계: 입력 검증(예: "LIVE" 텍스트 타이핑) 또는 OTP.

```tsx
const confirm = useConfirm();
const onSwitch = async () => {
  const ok = await confirm({
    title: '실거래 전환',
    body: 'LIVE 모드 진입 시 실제 주문이 발생합니다. 동의를 위해 "LIVE"를 입력하세요.',
    requireText: 'LIVE',
  });
  if (ok) await mutation.mutate();
};
```

---

## 9. 테스트 전략

| 레벨 | 도구 | 위치 |
|---|---|---|
| Unit | Vitest + RTL | `src/**/__tests__/` |
| Component | Storybook (선택) | `*.stories.tsx` |
| E2E | Playwright | `e2e/` |
| 시각 회귀 | Playwright snapshot | `e2e/visual/` |

- 핵심 시나리오: 로그인, 모드 전환, 주문 생성, 백테스트 실행, Kill Switch.

---

## 10. 환경변수 (Next.js)

| 변수 | 설명 |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | 백엔드 API base URL |
| `NEXT_PUBLIC_WS_BASE_URL` | WebSocket base URL |
| `NEXT_PUBLIC_APP_ENV` | development / staging / production |
| `NEXT_PUBLIC_SENTRY_DSN` (옵션) | 에러 트래킹 |

---

## 11. 빌드 / 배포

- `pnpm build` → `.next/standalone` 모드로 빌드 → Dockerfile에서 복사.
- 정적 자산은 nginx에서 직접 서빙(`/_next/static/*`) 옵션.
- 환경별 빌드 시점에 `NEXT_PUBLIC_*` 인라인.

---

## 12. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | DevLead | 최초 작성 |
