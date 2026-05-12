'use client';

import { useEffect, type ReactNode } from 'react';

import { useMe } from '@/lib/api/queries/auth';
import { session } from '@/lib/auth/session';
import { useAuthStore } from '@/stores/auth-store';
import { useTradeModeStore } from '@/stores/trade-mode-store';

/**
 * 앱 마운트 시 토큰 보유 시 /users/me 호출하여 user/모드 동기화.
 * - 모드는 서버 값과 일치시키되, LIVE 전환 시도는 UI에서 별도 검증.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const setUser = useAuthStore((s) => s.setUser);
  const setLoading = useAuthStore((s) => s.setLoading);
  const setMode = useTradeModeStore((s) => s.setMode);

  const hasToken = typeof window !== 'undefined' && !!session.get();
  const me = useMe();

  useEffect(() => {
    if (!hasToken) {
      setUser(null);
      return;
    }
    setLoading(me.isFetching);
    if (me.data) {
      setUser(me.data);
      // 서버 모드와 강제 동기화 (confirmed=true: 이미 서버에서 인증된 모드)
      setMode(me.data.trade_mode, { confirmed: true });
    }
    if (me.isError) {
      setUser(null);
    }
  }, [hasToken, me.data, me.isError, me.isFetching, setUser, setLoading, setMode]);

  return <>{children}</>;
}
