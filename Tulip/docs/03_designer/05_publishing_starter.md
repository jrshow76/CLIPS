# 퍼블리싱 스타터 가이드 (Publishing Starter)

| 항목 | 내용 |
|---|---|
| 문서명 | Tulip+ 퍼블리싱 스타터 가이드 |
| 문서 ID | DSN-05 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | Designer Agent |
| 검토자 | PM, DevLead, FrontendSenior |
| 상태 | 초안 |

---

## 1. 문서 목적

Designer가 작성한 디자인 시스템(DSN-02)·컴포넌트 라이브러리(DSN-03)·와이어프레임(DSN-04)을 **Next.js + Tailwind 기반 코드**로 옮기기 위한 토큰·디렉토리·인수인계 가이드를 제공한다. 본 문서는 FrontendSenior가 컴포넌트 골격을 즉시 구현할 수 있도록 작성된 실무 스타터다.

---

## 2. 기술 스택 & 전제

| 구분 | 채택 |
|---|---|
| 프레임워크 | Next.js 15+ (App Router) |
| 언어 | TypeScript 5 |
| 스타일 | Tailwind CSS 3 + CSS Variables(토큰) |
| 상태 | TanStack Query 5 |
| 폼 | React Hook Form + Zod |
| 컴포넌트 표준 | Headless: Radix UI / cmdk / react-aria 부분 채택 |
| 차트 | Recharts (Lazy) |
| 아이콘 | lucide-react |
| 폰트 | Pretendard Variable (next/font + self-host) |
| 테스트 | Vitest + React Testing Library, Playwright(E2E) |
| 스토리북 | Storybook 8 |

---

## 3. 디렉토리 구조 권고

```
src/
├─ app/                         # Next.js App Router
│  ├─ (admin)/                  # 사서/관리자 라우트 그룹
│  │  ├─ dashboard/page.tsx
│  │  ├─ cataloging/
│  │  │  ├─ search/page.tsx
│  │  │  └─ marc/[id]/page.tsx
│  │  └─ layout.tsx             # AdminShell
│  ├─ (opac)/                   # OPAC 라우트 그룹
│  │  ├─ page.tsx               # 홈
│  │  ├─ search/page.tsx
│  │  ├─ items/[id]/page.tsx
│  │  └─ layout.tsx             # OPACShell
│  ├─ (kiosk)/                  # 키오스크 라우트 그룹
│  │  └─ layout.tsx             # KioskShell
│  └─ globals.css               # 토큰 변수
│
├─ components/
│  ├─ atoms/
│  │  ├─ Button.tsx
│  │  ├─ Input.tsx
│  │  └─ ...
│  ├─ molecules/
│  │  ├─ FormField.tsx
│  │  ├─ SearchBar.tsx
│  │  └─ ...
│  ├─ organisms/
│  │  ├─ Table/
│  │  ├─ MarcEditor/
│  │  ├─ SeatMap/
│  │  └─ ...
│  ├─ templates/
│  │  ├─ AdminShell.tsx
│  │  ├─ OPACShell.tsx
│  │  └─ KioskShell.tsx
│  └─ patterns/
│     ├─ ListPage.tsx
│     ├─ DetailPage.tsx
│     ├─ EditorPage.tsx
│     ├─ DashboardPage.tsx
│     ├─ WizardPage.tsx
│     └─ CounterPage.tsx
│
├─ design-tokens/
│  ├─ tokens.ts                 # 코드용 토큰
│  ├─ tokens.css                # CSS 변수 (라이트/다크)
│  └─ tokens.json               # Style Dictionary 원본
│
├─ lib/
│  ├─ api/                      # TanStack Query 클라이언트
│  ├─ a11y/                     # 키보드·포커스 유틸
│  └─ format/                   # 날짜·통화·KORMARC 포맷
│
├─ hooks/                       # 공통 훅
├─ types/                       # 도메인 타입 (Biblio, Item, Member ...)
└─ styles/
   └─ fonts/                    # self-host Pretendard
```

### 명명 규칙

- 컴포넌트: `PascalCase.tsx` (예: `BookCard.tsx`)
- 훅: `useXxx.ts`
- 유틸: `camelCase.ts`
- 토큰: `kebab-case` (CSS 변수), `camelCase` (TS export)
- 도메인 컴포넌트 prefix: 도메인 약어 사용 권장 (`CatMarcEditor`, `CirCounterPanel`)

---

## 4. 디자인 토큰 코드 예시

### 4.1 `tokens.ts` (TypeScript export)

```ts
// src/design-tokens/tokens.ts
export const color = {
  primary: {
    50: 'var(--color-primary-50)',
    100: 'var(--color-primary-100)',
    500: 'var(--color-primary-500)',
    600: 'var(--color-primary-600)',
    700: 'var(--color-primary-700)',
  },
  secondary: {
    500: 'var(--color-secondary-500)',
    600: 'var(--color-secondary-600)',
  },
  neutral: {
    0: 'var(--color-neutral-0)',
    50: 'var(--color-neutral-50)',
    100: 'var(--color-neutral-100)',
    300: 'var(--color-neutral-300)',
    500: 'var(--color-neutral-500)',
    700: 'var(--color-neutral-700)',
    900: 'var(--color-neutral-900)',
  },
  semantic: {
    success: 'var(--color-success-500)',
    warning: 'var(--color-warning-500)',
    danger: 'var(--color-danger-500)',
    info: 'var(--color-info-500)',
  },
  surface: {
    app: 'var(--surface-app)',
    card: 'var(--surface-card)',
    raised: 'var(--surface-raised)',
  },
  domain: {
    acq: '#F97316',
    cat: '#8B5CF6',
    cir: '#0EA5E9',
    col: '#84CC16',
    acs: '#EF4444',
    fac: '#14B8A6',
  },
} as const;

export const space = {
  0: '0',
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
} as const;

export const radius = {
  none: '0',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '24px',
  full: '9999px',
} as const;

export const shadow = {
  sm: '0 1px 2px rgba(0,0,0,0.06)',
  md: '0 4px 12px rgba(0,0,0,0.08)',
  lg: '0 12px 32px rgba(0,0,0,0.10)',
  xl: '0 24px 48px rgba(0,0,0,0.16)',
  focus: '0 0 0 3px rgba(219,39,119,0.35)',
} as const;

export const motion = {
  fast: '120ms cubic-bezier(.2,0,0,1)',
  base: '200ms cubic-bezier(.2,0,0,1)',
  slow: '320ms cubic-bezier(.2,0,0,1)',
} as const;

export const breakpoint = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
  '3xl': '1920px',
} as const;

export const font = {
  sans: `'Pretendard Variable', 'Noto Sans KR', system-ui, sans-serif`,
  serif: `'Noto Serif KR', 'Source Serif', serif`,
  mono: `'JetBrains Mono', 'D2Coding', monospace`,
} as const;

export const text = {
  display: { size: '36px', lineHeight: '44px', weight: 700 },
  h1: { size: '28px', lineHeight: '36px', weight: 700 },
  h2: { size: '22px', lineHeight: '30px', weight: 600 },
  h3: { size: '18px', lineHeight: '26px', weight: 600 },
  body: { size: '14px', lineHeight: '22px', weight: 400 },
  bodyLg: { size: '16px', lineHeight: '24px', weight: 400 },
  caption: { size: '12px', lineHeight: '18px', weight: 400 },
  overline: { size: '11px', lineHeight: '16px', weight: 600, tracking: '0.06em' },
} as const;
```

### 4.2 `tokens.css` (CSS 변수)

```css
/* src/design-tokens/tokens.css */
:root {
  /* Brand */
  --color-primary-50: #FDF2F8;
  --color-primary-100: #FCE7F3;
  --color-primary-500: #DB2777;
  --color-primary-600: #BE185D;
  --color-primary-700: #9D174D;

  --color-secondary-500: #10B981;
  --color-secondary-600: #059669;

  /* Neutral */
  --color-neutral-0: #FFFFFF;
  --color-neutral-50: #FAFAFA;
  --color-neutral-100: #F4F4F5;
  --color-neutral-300: #D4D4D8;
  --color-neutral-500: #71717A;
  --color-neutral-700: #3F3F46;
  --color-neutral-900: #18181B;

  /* Semantic */
  --color-success-500: #16A34A;
  --color-warning-500: #F59E0B;
  --color-danger-500: #DC2626;
  --color-info-500: #2563EB;

  /* Surface */
  --surface-app: #FAFAFA;
  --surface-card: #FFFFFF;
  --surface-raised: #FFFFFF;

  /* Focus */
  --ring-focus: 0 0 0 3px rgba(219,39,119,0.35);
}

:root[data-theme="dark"] {
  --color-primary-500: #DB2777;
  --color-primary-600: #EC4899;
  --color-neutral-0: #0A0A0B;
  --color-neutral-50: #111114;
  --color-neutral-100: #18181B;
  --color-neutral-300: #3F3F46;
  --color-neutral-500: #71717A;
  --color-neutral-700: #D4D4D8;
  --color-neutral-900: #FAFAFA;
  --surface-app: #0A0A0B;
  --surface-card: #18181B;
  --surface-raised: #27272A;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: 0ms !important; animation-duration: 0ms !important; }
}
```

### 4.3 `tailwind.config.ts`

```ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        primary: {
          50:  'var(--color-primary-50)',
          100: 'var(--color-primary-100)',
          500: 'var(--color-primary-500)',
          600: 'var(--color-primary-600)',
          700: 'var(--color-primary-700)',
        },
        secondary: {
          500: 'var(--color-secondary-500)',
          600: 'var(--color-secondary-600)',
        },
        neutral: {
          0:   'var(--color-neutral-0)',
          50:  'var(--color-neutral-50)',
          100: 'var(--color-neutral-100)',
          300: 'var(--color-neutral-300)',
          500: 'var(--color-neutral-500)',
          700: 'var(--color-neutral-700)',
          900: 'var(--color-neutral-900)',
        },
        success: 'var(--color-success-500)',
        warning: 'var(--color-warning-500)',
        danger:  'var(--color-danger-500)',
        info:    'var(--color-info-500)',
        surface: {
          app:    'var(--surface-app)',
          card:   'var(--surface-card)',
          raised: 'var(--surface-raised)',
        },
        domain: {
          acq: '#F97316', cat: '#8B5CF6', cir: '#0EA5E9',
          col: '#84CC16', acs: '#EF4444', fac: '#14B8A6',
        },
      },
      spacing: {
        1: '4px',  2: '8px',  3: '12px', 4: '16px',
        5: '20px', 6: '24px', 8: '32px', 10: '40px',
        12: '48px', 16: '64px',
      },
      borderRadius: {
        sm: '4px', md: '8px', lg: '12px', xl: '16px', '2xl': '24px', full: '9999px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(0,0,0,0.06)',
        md: '0 4px 12px rgba(0,0,0,0.08)',
        lg: '0 12px 32px rgba(0,0,0,0.10)',
        xl: '0 24px 48px rgba(0,0,0,0.16)',
        focus: '0 0 0 3px rgba(219,39,119,0.35)',
      },
      fontFamily: {
        sans: ['Pretendard Variable', 'Noto Sans KR', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'D2Coding', 'monospace'],
      },
      screens: {
        sm: '640px', md: '768px', lg: '1024px',
        xl: '1280px', '2xl': '1536px', '3xl': '1920px',
      },
      transitionDuration: {
        fast: '120ms', base: '200ms', slow: '320ms',
      },
    },
  },
  plugins: [require('@tailwindcss/forms'), require('@tailwindcss/typography')],
};

export default config;
```

### 4.4 Pretendard 폰트 로드 (`app/layout.tsx`)

```tsx
import localFont from 'next/font/local';
import './globals.css';
import '../design-tokens/tokens.css';

const pretendard = localFont({
  src: '../styles/fonts/PretendardVariable.woff2',
  display: 'swap',
  weight: '45 920',
  variable: '--font-sans',
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={pretendard.variable}>
      <body className="bg-surface-app text-neutral-900 font-sans antialiased">{children}</body>
    </html>
  );
}
```

---

## 5. 컴포넌트 작성 컨벤션

### 5.1 Button 예시

```tsx
// src/components/atoms/Button.tsx
import { forwardRef } from 'react';
import { clsx } from 'clsx';

type Variant = 'primary' | 'secondary' | 'tertiary' | 'ghost' | 'danger' | 'link';
type Size = 'xs' | 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

const variantStyles: Record<Variant, string> = {
  primary:   'bg-primary-500 text-neutral-0 hover:bg-primary-600 active:bg-primary-700',
  secondary: 'bg-neutral-100 text-neutral-900 hover:bg-neutral-300/40 border border-neutral-300',
  tertiary:  'bg-transparent text-primary-600 hover:bg-primary-50',
  ghost:     'bg-transparent text-neutral-700 hover:bg-neutral-100',
  danger:    'bg-danger text-neutral-0 hover:opacity-90',
  link:      'bg-transparent text-primary-600 underline-offset-4 hover:underline',
};

const sizeStyles: Record<Size, string> = {
  xs: 'h-6 px-2 text-[12px] gap-1',
  sm: 'h-8 px-3 text-[13px] gap-1.5',
  md: 'h-10 px-4 text-[14px] gap-2',
  lg: 'h-12 px-5 text-[16px] gap-2',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading, leftIcon, rightIcon, fullWidth, className, children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={clsx(
        'inline-flex items-center justify-center rounded-md font-semibold transition-colors',
        'focus-visible:outline-none focus-visible:shadow-focus',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variantStyles[variant],
        sizeStyles[size],
        fullWidth && 'w-full',
        className,
      )}
      {...rest}
    >
      {leftIcon}
      {children}
      {rightIcon}
    </button>
  );
});
```

### 5.2 BookCard 예시 (도메인 컴포넌트)

```tsx
// src/components/organisms/BookCard/BookCard.tsx
import Image from 'next/image';
import { Badge } from '@/components/atoms/Badge';

export interface BookCardProps {
  biblio: { id: string; title: string; author: string; publisher: string; year: number; coverUrl?: string };
  holdings?: { available: number; total: number; reserved?: number };
  variant?: 'cover-large' | 'cover-list' | 'compact' | 'shelf';
  onClick?: () => void;
}

export function BookCard({ biblio, holdings, variant = 'cover-list', onClick }: BookCardProps) {
  // ... variant별 레이아웃
}
```

---

## 6. 접근성 코드 가이드

| 항목 | 코드 |
|---|---|
| 포커스링 | `focus-visible:shadow-focus` (Tailwind plugin) |
| 키보드 모달 | `react-aria` / `radix-ui Dialog` 채택 |
| 라이브 영역 | Toast: `role="status"` (info) / `role="alert"` (danger) |
| 라벨 | `<label htmlFor>` 필수, FormField 컴포넌트로 강제 |
| ARIA | 아이콘 버튼 `aria-label`, 인디케이터 `aria-hidden="true"` |
| 시각·동작 | `prefers-reduced-motion` 토큰 transition 0 |

---

## 7. 디자인 → 개발 협업 절차

### 7.1 토큰 전달 워크플로

```
Figma Variables (Designer)
        ↓ export
   tokens.json (Style Dictionary 호환)
        ↓ npx style-dictionary build
  ┌─────────┬─────────┬──────────────┐
tokens.ts  tokens.css tailwind.config.ts
```

| 단계 | 담당 | 결과물 |
|---|---|---|
| Figma 토큰 정의 | Designer | Variables collection |
| Tokens JSON export | Designer | `tokens.json` 커밋 |
| 코드 변환 빌드 | FE 자동화 | `tokens.ts`, `tokens.css`, `tailwind.config.ts` |
| 컴포넌트 매핑 | FrontendSenior | atoms/molecules 구현 |
| 스토리북 등록 | FrontendSenior | Storybook stories |

### 7.2 화면 퍼블리싱 → 컴포넌트화 절차

1. **Designer** Figma 디자인 확정 → HTML/CSS 퍼블리싱 파일 작성 (정적, 시맨틱 마크업).
2. **Designer → FrontendSenior** 퍼블리싱 zip + Notion 인수인계 문서 전달.
3. **FrontendSenior** 페이지를 Next.js 라우트로 매핑, 컴포넌트 분리, props 정의.
4. **FrontendDev** API 연동(TanStack Query) + 폼 검증(Zod) 추가.
5. **Designer** 디자인 QA(픽셀·간격·색상) 검수, 이슈는 GitHub Issue로 회수.
6. **QA** 기능·접근성 테스트.

### 7.3 변경 관리

- 토큰 변경 → `tokens.json` PR → CI 빌드 → Storybook 시각 회귀 → 머지
- 컴포넌트 API 변경 → CHANGELOG.md 명시, breaking 변경은 메이저
- Figma 변경 → 디자인 리뷰 회의(주 1회) → 토큰 PR

---

## 8. FrontendSenior 인수인계 체크리스트

### 8.1 디자인 시스템 코드 변환

- [ ] `tokens.json` 커밋 및 빌드 스크립트 동작 확인
- [ ] `tokens.css` / `tokens.ts` / `tailwind.config.ts` 3종 생성
- [ ] 라이트·다크 모드 토글 동작 (`data-theme` 속성)
- [ ] Pretendard 폰트 self-host 적용, FOUT 최소화
- [ ] Lucide 아이콘 패키지 추가, 도메인 자체 아이콘 SVG 추가
- [ ] `focus-visible` 글로벌 포커스링 적용
- [ ] `prefers-reduced-motion` 미디어쿼리 전역 적용

### 8.2 Atomic 컴포넌트 구현

- [ ] Atoms (10개) — Button, IconButton, Input, Textarea, Select/Combobox, Checkbox/Radio/Switch, Badge, Avatar, Skeleton, Tooltip
- [ ] Molecules (11개) — FormField, SearchBar, Pagination, DatePicker, FileUpload, Stepper, Tabs, Breadcrumb, Toast, EmptyState, KeyValueList
- [ ] Organisms 우선 6종 — Table, Modal, Drawer, NotificationCenter, GlobalCommandPalette, BookCard

### 8.3 도서관 특화 컴포넌트

- [ ] MarcEditor 골격 (필드 그리드, 단축키)
- [ ] BarcodeInput (USB HID 입력 처리)
- [ ] RfidPanel 인터페이스 정의 (실제 디바이스 연동은 BackendSenior와 협의)
- [ ] SeatMap 인터랙티브 SVG/Canvas

### 8.4 페이지 셸 & 라우팅

- [ ] AdminShell (Sidebar + Header + Breadcrumb)
- [ ] OPACShell (Header + Footer + 모바일 하단탭)
- [ ] KioskShell (전체화면 + 자동 idle 타이머)
- [ ] 메뉴 ID(`M-...`) 기반 라우트 매핑 테이블

### 8.5 품질·테스트

- [ ] Storybook 8 구성 및 모든 Atom·Molecule 등록
- [ ] axe-core 자동 a11y 테스트 통합
- [ ] Playwright E2E 스모크 (로그인·검색·대출·예약)
- [ ] 시각 회귀 (Chromatic 또는 Loki) — 선택

### 8.6 문서

- [ ] 컴포넌트 README (props·예시·a11y)
- [ ] 디자인 토큰 사용 가이드
- [ ] FrontendDev 온보딩 가이드

---

## 9. 명명 규약 요약 표

| 항목 | 규약 | 예시 |
|---|---|---|
| 메뉴 ID | `M-{도메인}-{대분류}-{중분류}` | `M-CAT-03-02` |
| 화면 ID | `SCR-{도메인}-{역할}-{번호}` | `SCR-CAT-A-002` |
| 컴포넌트 | PascalCase, 도메인 prefix 선택 | `BookCard`, `CatMarcEditor` |
| 라우트 경로 | kebab-case | `/cataloging/marc/[id]` |
| CSS 변수 | `--{카테고리}-{이름}-{단계}` | `--color-primary-500` |
| Tailwind 토큰 | camelCase 또는 kebab-case | `bg-primary-500` |
| 디자인 토큰 TS | camelCase | `color.primary[500]` |
| 도메인 코드 | 3글자 대문자 | CMN/ACQ/CAT/CIR/COL/ACS/FAC/STA/SYS |

---

## 10. 후속 작업 & 의존성

| 작업 | 의존 |
|---|---|
| Figma Variables → tokens.json 자동화 | Designer + 도구 도입(Style Dictionary, Figma Tokens 플러그인) |
| Storybook 초기 구성 | FrontendSenior |
| 12개 우선 화면 퍼블리싱 | Designer |
| API 모킹 (MSW) | FrontendSenior + BackendSenior(스펙 협의) |
| 접근성 자동검사 CI | FrontendSenior + QA |

---

## 11. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v0.1 | 2026-05-11 | Designer Agent | 최초 작성 |
