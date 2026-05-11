'use client';

import { ToastProvider } from '@tulip/ui';
import { type ReactNode } from 'react';

import { QueryProvider } from './QueryProvider';
import { ThemeProvider } from './ThemeProvider';

/**
 * 전역 Provider 묶음.
 * - ThemeProvider: data-theme 속성으로 light/dark 전환
 * - QueryProvider: TanStack Query
 * - ToastProvider: 토스트 시스템
 *
 * Phase 1-B에서 AuthProvider 추가 예정.
 */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <QueryProvider>
        <ToastProvider>{children}</ToastProvider>
      </QueryProvider>
    </ThemeProvider>
  );
}
