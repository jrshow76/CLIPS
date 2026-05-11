'use client';

import { AuthProvider as BaseAuthProvider, useAuth } from '@tulip/auth';
import { useEffect, type ReactNode } from 'react';

import { authClient, setActiveTenantId } from '@/lib/auth/client';

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
