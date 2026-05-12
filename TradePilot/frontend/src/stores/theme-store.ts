import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export type ThemeMode = 'dark' | 'light';

interface ThemeState {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  toggle: () => void;
}

/**
 * 다크/라이트 테마 토글.
 * - data-theme 속성을 html 루트에 적용 (tokens.css가 이를 기준으로 변수 전환).
 * - SSR 시 hydration mismatch를 막기 위해 ThemeProvider에서 마운트 후 동기화.
 */
export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      setTheme: (theme) => {
        set({ theme });
        if (typeof document !== 'undefined') {
          document.documentElement.dataset.theme = theme;
        }
      },
      toggle: () => {
        const next: ThemeMode = get().theme === 'dark' ? 'light' : 'dark';
        get().setTheme(next);
      },
    }),
    {
      name: 'tp.theme',
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
