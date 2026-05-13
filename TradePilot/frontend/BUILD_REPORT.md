# TradePilot Frontend Build Report

본 문서는 TradePilot 프론트엔드 프로젝트의 의존성 정상화, lint, type check, production build 통과 작업 결과 보고서이다.

## 1. 최종 결과 요약

| 단계 | 명령어 | 결과 |
|---|---|---|
| 1. 의존성 설치 | `npm install` | PASS (470 packages) |
| 2. Lint | `npm run lint` | PASS (No ESLint warnings or errors) |
| 3. Type Check | `npx tsc --noEmit` | PASS (0 errors) |
| 4. Production Build | `npm run build` | PASS (27 routes, 53.7s) |

## 2. 환경

- Node.js: v22.22.2
- npm: 10.9.7
- Next.js: 14.2.4 (App Router)
- TypeScript: ^5.4.5 (strict mode)
- 작업 디렉토리: `/home/user/CLIPS/TradePilot/frontend/`

## 3. 발견한 에러 종류별 통계

| 분류 | 발견 건수 | 파일 수 |
|---|---|---|
| TypeScript 에러 (axios 타입 augmentation 누락) | 3건 | 2개 파일 (`orders.ts`, `settings.ts`) |
| TypeScript 에러 (인터페이스 상속 충돌 - `title` 속성) | 1건 | 1개 파일 (`card.tsx`) |
| TypeScript 에러 (TanStack Query keyFn 인덱스 시그니처 불일치) | 1건 | 1개 파일 (`trades.ts`) |
| TypeScript 에러 (react-hook-form Resolver 시그니처 부적합) | 1건 | 1개 파일 (`zod-resolver.ts`) |
| Lint 에러 | 0건 | - |
| Build 에러 | 0건 (TS 수정 후) | - |
| **총 TS 에러** | **6건** | **5개 파일** |

## 4. 수정 내역 (파일별 요약)

### 4.1 `src/lib/api/client.ts`
- **문제**: `axios` 모듈 augmentation에서 `InternalAxiosRequestConfig`에만 `requireTradeMode`/`idempotent`/`__retried` 필드를 추가했음. 그러나 호출 측 코드(`api.post(url, data, { requireTradeMode: true })`)는 `AxiosRequestConfig`(public) 타입을 통해 전달하므로 TS2353 발생.
- **수정**: `AxiosRequestConfig` 인터페이스에도 동일한 옵션 필드를 추가 augmentation. 두 인터페이스 모두에 선언하여 public/internal 양쪽 일관성 유지.

### 4.2 `src/components/ui/card.tsx`
- **문제**: `SectionProps extends HTMLAttributes<HTMLDivElement>`에서 `title?: ReactNode`이 native `title?: string`을 좁은 타입으로 덮어쓰려 시도하여 TS2430 발생.
- **수정**: `Omit<HTMLAttributes<HTMLDivElement>, 'title'>` 후 `title?: ReactNode` 재선언.

### 4.3 `src/lib/api/queries/trades.ts`
- **문제**: `queryKeys.trades.list(filter)`의 시그니처가 `Record<string, unknown> | undefined`인데 `TradeFilter`는 별도 인터페이스라서 인덱스 시그니처가 없어 TS2345 발생.
- **수정**: `queryKeys.trades.list(filter as Record<string, unknown> | undefined)`로 명시 캐스트. (`TradeFilter` 자체에 인덱스 시그니처를 추가하면 타입 안정성이 떨어지므로 호출부에서만 캐스팅.)

### 4.4 `src/lib/forms/zod-resolver.ts`
- **문제**: react-hook-form의 `Resolver` 반환 타입은 `ResolverSuccess`(에러가 `Record<string, never>`)와 `ResolverError`(values가 `Record<string, never>`)의 union. 자체 구현이 빈 객체 `{}`을 그대로 반환하여 union 한 쪽에 매핑되지 못함.
- **수정**: 성공 시 `errors: {} as Record<string, never>`, 실패 시 `values: {} as Record<string, never>`로 명시. 외부 사용 API/시그니처는 그대로 유지.

## 5. 의존성 변경

### 5.1 추가한 의존성
**없음.** `package.json`에 정의된 의존성만으로 lint/tsc/build 모두 통과함.
- FrontendDev가 react-hook-form용 `zodResolver`를 자체 구현 (`src/lib/forms/zod-resolver.ts`)했기 때문에 `@hookform/resolvers` 미설치로도 동작.
- `@types/uuid`, `@types/node`, `@types/react`, `@types/react-dom`은 모두 `package.json`에 이미 명시.

### 5.2 제거한 의존성
**없음.**

### 5.3 의존성 설치 시 경고 (참고용)
- 일부 deprecated 경고 (`inflight@1.0.6`, `rimraf@3.0.2`, `glob@7.2.3`, `eslint@8.57.1`, `uuid@9.0.1`, `next@14.2.4`)는 transitive/직접 의존성에서 발생. 빌드 차단 요인 아님.
- 8건의 npm audit vulnerability(critical 1, high 6, moderate 1) 존재. `npm audit fix` 또는 의존성 메이저 버전 업그레이드는 의도된 의존성 표(특히 Next.js 14.2.4 고정)와 충돌 가능성이 있어 본 작업 범위에서 제외.

## 6. 최종 빌드 출력 요약

- **빌드 시간**: 53.7초 (clean build, `.next` 디렉토리 제거 후)
- **총 라우트 수**: 27개
  - Static (○): 21개
  - Dynamic (ƒ): 6개 (`[id]`, `[code]` 파라미터 라우트)
- **First Load JS shared by all**: 87.6 kB
  - `chunks/7023-*.js`: 31.7 kB
  - `chunks/fd9d1056-*.js`: 53.6 kB
  - other shared chunks: 2.23 kB
- **First Load JS 최대 페이지**: `/report` 260 kB, `/chart/[code]` 255 kB (lightweight-charts/recharts 적재)
- **First Load JS 최소 페이지**: `/`, `/_not-found` 87.7 kB (shared만)

### 주요 페이지 사이즈 (페이지 자체 + First Load)
| 라우트 | 종류 | Size | First Load JS |
|---|---|---|---|
| `/dashboard` | Static | 10.3 kB | 162 kB |
| `/chart/[code]` | Dynamic | 14.8 kB | 255 kB |
| `/auto-trading` | Static | 5.75 kB | 150 kB |
| `/auto-trading/limits` | Static | 7.24 kB | 174 kB |
| `/backtest` | Static | 7.46 kB | 175 kB |
| `/backtest/[id]` | Dynamic | 6.73 kB | 151 kB |
| `/sectors/flow` | Static | 1.3 kB | 149 kB |
| `/login` | Static | 11.2 kB | 178 kB |
| `/report` | Static | 10.3 kB | 260 kB |

## 7. 알려진 한계 및 후속 권고

1. **dev server 미실행**: 본 환경에서는 `npm run dev` 동작 검증을 수행하지 않음. SSR/CSR 경계나 API rewrites는 빌드 통과 기준으로만 확인.
2. **API/백엔드 미연동**: 현재 코드는 `_mock-helpers.ts` 기반 mock 모드를 다수 사용 중. 실서버 연동 시 응답 타입/envelope 일치 검증 필요.
3. **Next.js 14.2.4 보안 권고**: 빌드는 통과하나 보안 패치된 버전으로 마이너 업그레이드 검토 권장 (DevLead 협의 필요).
4. **uuid v9 deprecated**: 기능 동작에는 영향 없음. 추후 v11 마이그레이션 검토 가능.
5. **lightweight-charts/recharts 동시 사용**: 일부 페이지에서 두 차트 라이브러리가 모두 로드되어 First Load JS가 250 kB을 넘는 경우 존재 (`/chart/[code]`, `/report`). 차트 라이브러리 통일 또는 dynamic import 분리 검토 가능 (성능 최적화 후속 과제).
6. **`@hookform/resolvers` 미설치 정책 유지**: FrontendSenior 가이드대로 자체 `zodResolver` 사용 중. 향후 `useForm` 사용처가 늘어나면 표준 라이브러리 도입 재검토 가능.

## 8. 검증 명령

```bash
cd /home/user/CLIPS/TradePilot/frontend
npm install                # PASS
npm run lint               # PASS
npx tsc --noEmit           # PASS
npm run build              # PASS (53.7s, 27 routes)
```
