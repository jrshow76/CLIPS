'use client';

import { useEffect, type ReactNode } from 'react';

import { useThemeStore } from '@/stores/theme-store';

/**
 * data-theme 속성을 root html에 동기화.
 * - SSR로 렌더된 default(dark)와 localStorage 값이 다를 때 hydration mismatch를 막기 위해
 *   suppressHydrationWarning을 RootLayout html에 부여.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.dataset.theme = theme;
    }
  }, [theme]);

  return <>{children}</>;
}
