'use client';

import { useRouter } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';

import { AppShell } from '@/components/layout/AppShell';
import { ROUTES } from '@/lib/constants';
import { session } from '@/lib/auth/session';
import { useAuthStore } from '@/stores/auth-store';

/**
 * 인증된 사용자용 레이아웃 + 가드.
 * - 토큰 없으면 /login으로 즉시 리다이렉트.
 * - useMe 결과는 AuthProvider가 zustand에 동기화.
 *
 * 운영 환경에서는 middleware.ts(엣지)로 옮겨 SSR 단계 가드 추가 권장 (FrontendDev 인계).
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    const hasToken = typeof window !== 'undefined' && !!session.get();
    if (!hasToken && !isAuthenticated) {
      // mock 모드(NEXT_PUBLIC_USE_MOCK=true)에서는 임시 토큰을 부여하여 데모 가능하게 함.
      if (process.env.NEXT_PUBLIC_USE_MOCK === 'true') {
        session.set({ access_token: 'mock.access.token', refresh_token: 'mock.refresh.token', expires_in: 3600 });
        return;
      }
      router.replace(ROUTES.LOGIN);
    }
  }, [isAuthenticated, router]);

  return <AppShell>{children}</AppShell>;
}
