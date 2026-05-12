import type { Config } from 'tailwindcss';

/**
 * Designer가 정의한 tokens.css의 CSS 변수를 Tailwind theme로 매핑.
 * - 색상은 CSS 변수 참조 (var(--color-*)) → 다크/라이트 토글 일원화.
 * - Tailwind 유틸과 BEM 컴포넌트 클래스를 혼용할 수 있도록 prefix 미지정.
 */
const config: Config = {
  content: ['./src/**/*.{ts,tsx,mdx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    container: {
      center: true,
      padding: '1rem',
      screens: {
        '2xl': '1440px',
      },
    },
    extend: {
      colors: {
        brand: {
          50: 'var(--color-brand-50)',
          100: 'var(--color-brand-100)',
          200: 'var(--color-brand-200)',
          300: 'var(--color-brand-300)',
          400: 'var(--color-brand-400)',
          500: 'var(--color-brand-500)',
          600: 'var(--color-brand-600)',
          700: 'var(--color-brand-700)',
          800: 'var(--color-brand-800)',
          900: 'var(--color-brand-900)',
        },
        bg: {
          0: 'var(--color-bg-0)',
          1: 'var(--color-bg-1)',
          2: 'var(--color-bg-2)',
          3: 'var(--color-bg-3)',
          4: 'var(--color-bg-4)',
        },
        border: {
          1: 'var(--color-border-1)',
          2: 'var(--color-border-2)',
          3: 'var(--color-border-3)',
        },
        fg: {
          1: 'var(--color-text-1)',
          2: 'var(--color-text-2)',
          3: 'var(--color-text-3)',
          inv: 'var(--color-text-inv)',
        },
        up: 'var(--color-up)',
        'up-soft': 'var(--color-up-soft)',
        down: 'var(--color-down)',
        'down-soft': 'var(--color-down-soft)',
        flat: 'var(--color-flat)',
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        danger: 'var(--color-danger)',
        info: 'var(--color-info)',
        mode: {
          sim: 'var(--color-mode-sim)',
          live: 'var(--color-mode-live)',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
      fontSize: {
        '12': 'var(--fs-12)',
        '13': 'var(--fs-13)',
        '14': 'var(--fs-14)',
        '15': 'var(--fs-15)',
        '16': 'var(--fs-16)',
        '18': 'var(--fs-18)',
        '20': 'var(--fs-20)',
        '24': 'var(--fs-24)',
        '28': 'var(--fs-28)',
        '32': 'var(--fs-32)',
        '40': 'var(--fs-40)',
      },
      spacing: {
        '0': 'var(--space-0)',
        '1': 'var(--space-1)',
        '2': 'var(--space-2)',
        '3': 'var(--space-3)',
        '4': 'var(--space-4)',
        '5': 'var(--space-5)',
        '6': 'var(--space-6)',
        '8': 'var(--space-8)',
        '10': 'var(--space-10)',
        '12': 'var(--space-12)',
        '16': 'var(--space-16)',
      },
      borderRadius: {
        xs: 'var(--radius-xs)',
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        pill: 'var(--radius-pill)',
      },
      boxShadow: {
        '1': 'var(--shadow-1)',
        '2': 'var(--shadow-2)',
        '3': 'var(--shadow-3)',
        focus: 'var(--shadow-focus)',
      },
      transitionDuration: {
        fast: 'var(--dur-fast)',
        base: 'var(--dur-base)',
        slow: 'var(--dur-slow)',
      },
      zIndex: {
        base: '1',
        sticky: '100',
        header: '500',
        drawer: '800',
        modal: '1000',
        toast: '1100',
      },
      maxWidth: {
        container: 'var(--container-max)',
      },
    },
  },
  plugins: [],
};

export default config;
