'use client';

import { AuthProvider as BaseAuthProvider, useAuth } from '@tulip/auth';
import { useEffect, type ReactNode } from 'react';

import { authClient, setActiveTenantId } from '@/lib/auth/client';

/**
 * admin 전용 AuthProvider — singleton AuthClient 주입 + tenantId 동기화.
 *
 * useAuth.user.tenantId가 변경되면 ApiClient의 tenantProvider 캐시를 갱신해
 * 후속 API 호출에서 `X-Tenant-Id` 헤더가 정확히 첨부되도록 한다.
 */
function TenantSync() {
  const { user } = useAuth();
  useEffect(() => {
    setActiveTenantId(user?.tenantId ?? null);
  }, [user?.tenantId]);
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <BaseAuthProvider client={authClient}>
      <TenantSync />
      {children}
    </BaseAuthProvider>
  );
}
