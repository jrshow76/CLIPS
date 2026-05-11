'use client';

import { ToastProvider } from '@tulip/ui';
import { type ReactNode } from 'react';

import { AuthProvider } from './AuthProvider';
import { QueryProvider } from './QueryProvider';
import { ThemeProvider } from './ThemeProvider';

/**
 * 전역 Provider 묶음.
 * - ThemeProvider: data-theme 속성으로 light/dark 전환
 * - QueryProvider: TanStack Query
 * - AuthProvider: iam-service 세션 복원·로그인 흐름 (Phase 1-B)
 * - ToastProvider: 토스트 시스템
 */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <QueryProvider>
        <AuthProvider>
          <ToastProvider>{children}</ToastProvider>
        </AuthProvider>
      </QueryProvider>
    </ThemeProvider>
  );
}
