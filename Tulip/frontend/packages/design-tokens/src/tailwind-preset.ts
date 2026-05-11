/**
 * Tulip+ Tailwind CSS Preset
 * 각 앱의 tailwind.config 에서 `presets: [tulipPreset]` 으로 사용.
 */
import type { Config } from 'tailwindcss';

const preset: Partial<Config> = {
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
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
          DEFAULT: 'var(--color-primary-500)',
        },
        secondary: {
          500: 'var(--color-secondary-500)',
          600: 'var(--color-secondary-600)',
          700: 'var(--color-secondary-700)',
          DEFAULT: 'var(--color-secondary-500)',
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
        success: {
          DEFAULT: 'var(--color-success-500)',
          50: 'var(--color-success-50)',
        },
        warning: {
          DEFAULT: 'var(--color-warning-500)',
          50: 'var(--color-warning-50)',
        },
        danger: {
          DEFAULT: 'var(--color-danger-500)',
          50: 'var(--color-danger-50)',
        },
        info: {
          DEFAULT: 'var(--color-info-500)',
          50: 'var(--color-info-50)',
        },
        surface: {
          app: 'var(--surface-app)',
          card: 'var(--surface-card)',
          raised: 'var(--surface-raised)',
          overlay: 'var(--surface-overlay)',
          inverse: 'var(--surface-inverse)',
        },
        domain: {
          acq: '#F97316',
          cat: '#8B5CF6',
          cir: '#0EA5E9',
          col: '#84CC16',
          acs: '#EF4444',
          fac: '#14B8A6',
        },
      },
      spacing: {
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
      },
      borderRadius: {
        none: '0',
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '24px',
        full: '9999px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(0,0,0,0.06)',
        md: '0 4px 12px rgba(0,0,0,0.08)',
        lg: '0 12px 32px rgba(0,0,0,0.10)',
        xl: '0 24px 48px rgba(0,0,0,0.16)',
        focus: '0 0 0 3px rgba(219,39,119,0.35)',
      },
      fontFamily: {
        sans: [
          'Pretendard Variable',
          'Pretendard',
          'Noto Sans KR',
          'system-ui',
          'sans-serif',
        ],
        mono: ['JetBrains Mono', 'D2Coding', 'monospace'],
      },
      screens: {
        sm: '640px',
        md: '768px',
        lg: '1024px',
        xl: '1280px',
        '2xl': '1536px',
        '3xl': '1920px',
      },
      transitionDuration: {
        fast: '120ms',
        base: '200ms',
        slow: '320ms',
      },
      transitionTimingFunction: {
        tulip: 'cubic-bezier(.2,0,0,1)',
      },
      zIndex: {
        dropdown: '1000',
        sticky: '1100',
        drawer: '1200',
        modal: '1300',
        popover: '1400',
        toast: '1500',
        tooltip: '1600',
      },
      fontSize: {
        display: ['36px', { lineHeight: '44px', fontWeight: '700' }],
        h1: ['28px', { lineHeight: '36px', fontWeight: '700' }],
        h2: ['22px', { lineHeight: '30px', fontWeight: '600' }],
        h3: ['18px', { lineHeight: '26px', fontWeight: '600' }],
        h4: ['16px', { lineHeight: '24px', fontWeight: '600' }],
        'body-lg': ['16px', { lineHeight: '24px', fontWeight: '400' }],
        body: ['14px', { lineHeight: '22px', fontWeight: '400' }],
        'body-sm': ['13px', { lineHeight: '20px', fontWeight: '400' }],
        caption: ['12px', { lineHeight: '18px', fontWeight: '400' }],
        overline: [
          '11px',
          {
            lineHeight: '16px',
            fontWeight: '600',
            letterSpacing: '0.06em',
          },
        ],
      },
    },
  },
};

export default preset;
