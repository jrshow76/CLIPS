/**
 * Tulip+ 디자인 토큰 (TypeScript)
 *
 * CSS 변수 참조 기반 - 런타임 테마 전환은 `<html data-theme="dark">`로 처리.
 */

import type { TypographyStyle } from './types';

/** 컬러 — Brand · Secondary · Neutral · Semantic · Surface · Domain */
export const color = {
  primary: {
    50: 'var(--color-primary-50)',
    100: 'var(--color-primary-100)',
    200: 'var(--color-primary-200)',
    300: 'var(--color-primary-300)',
    400: 'var(--color-primary-400)',
    500: 'var(--color-primary-500)',
    600: 'var(--color-primary-600)',
    700: 'var(--color-primary-700)',
    800: 'var(--color-primary-800)',
    900: 'var(--color-primary-900)',
  },
  secondary: {
    500: 'var(--color-secondary-500)',
    600: 'var(--color-secondary-600)',
    700: 'var(--color-secondary-700)',
  },
  neutral: {
    0: 'var(--color-neutral-0)',
    50: 'var(--color-neutral-50)',
    100: 'var(--color-neutral-100)',
    200: 'var(--color-neutral-200)',
    300: 'var(--color-neutral-300)',
    400: 'var(--color-neutral-400)',
    500: 'var(--color-neutral-500)',
    600: 'var(--color-neutral-600)',
    700: 'var(--color-neutral-700)',
    800: 'var(--color-neutral-800)',
    900: 'var(--color-neutral-900)',
  },
  semantic: {
    success: 'var(--color-success-500)',
    successBg: 'var(--color-success-50)',
    warning: 'var(--color-warning-500)',
    warningBg: 'var(--color-warning-50)',
    danger: 'var(--color-danger-500)',
    dangerBg: 'var(--color-danger-50)',
    info: 'var(--color-info-500)',
    infoBg: 'var(--color-info-50)',
  },
  surface: {
    app: 'var(--surface-app)',
    card: 'var(--surface-card)',
    raised: 'var(--surface-raised)',
    overlay: 'var(--surface-overlay)',
    inverse: 'var(--surface-inverse)',
  },
  /**
   * 도서관 6 도메인 강조 컬러 — 차트·아이콘·뱃지 한정. 텍스트 색상 금지.
   */
  domain: {
    acq: '#F97316',
    cat: '#8B5CF6',
    cir: '#0EA5E9',
    col: '#84CC16',
    acs: '#EF4444',
    fac: '#14B8A6',
  },
} as const;

/** 8pt 그리드 간격 토큰 */
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

/** Border Radius */
export const radius = {
  none: '0',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '24px',
  full: '9999px',
} as const;

/** Shadow */
export const shadow = {
  sm: '0 1px 2px rgba(0,0,0,0.06)',
  md: '0 4px 12px rgba(0,0,0,0.08)',
  lg: '0 12px 32px rgba(0,0,0,0.10)',
  xl: '0 24px 48px rgba(0,0,0,0.16)',
  focus: '0 0 0 3px rgba(219,39,119,0.35)',
} as const;

/** Motion (transition) */
export const motion = {
  fast: '120ms cubic-bezier(.2,0,0,1)',
  base: '200ms cubic-bezier(.2,0,0,1)',
  slow: '320ms cubic-bezier(.2,0,0,1)',
  reduced: '0ms',
} as const;

/** Breakpoints */
export const breakpoint = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
  '3xl': '1920px',
} as const;

/** Font family */
export const font = {
  sans: `'Pretendard Variable', 'Pretendard', 'Noto Sans KR', system-ui, sans-serif`,
  serif: `'Noto Serif KR', 'Source Serif', serif`,
  mono: `'JetBrains Mono', 'D2Coding', monospace`,
} as const;

/** Type scale */
export const text: Record<string, TypographyStyle> = {
  display: { size: '36px', lineHeight: '44px', weight: 700, tracking: '-0.02em' },
  h1: { size: '28px', lineHeight: '36px', weight: 700, tracking: '-0.02em' },
  h2: { size: '22px', lineHeight: '30px', weight: 600 },
  h3: { size: '18px', lineHeight: '26px', weight: 600 },
  h4: { size: '16px', lineHeight: '24px', weight: 600 },
  bodyLg: { size: '16px', lineHeight: '24px', weight: 400 },
  body: { size: '14px', lineHeight: '22px', weight: 400 },
  bodySm: { size: '13px', lineHeight: '20px', weight: 400 },
  caption: { size: '12px', lineHeight: '18px', weight: 400 },
  overline: { size: '11px', lineHeight: '16px', weight: 600, tracking: '0.06em' },
  monoSm: { size: '13px', lineHeight: '20px', weight: 400 },
};

/** Z-index 계층 */
export const zIndex = {
  dropdown: 1000,
  sticky: 1100,
  drawer: 1200,
  modal: 1300,
  popover: 1400,
  toast: 1500,
  tooltip: 1600,
} as const;

export const tokens = {
  color,
  space,
  radius,
  shadow,
  motion,
  breakpoint,
  font,
  text,
  zIndex,
} as const;

export type Tokens = typeof tokens;
