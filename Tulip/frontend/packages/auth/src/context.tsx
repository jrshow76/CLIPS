/**
 * AuthProvider — React Context 기반 인증 상태 관리
 */
import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { type AuthClient } from './client';
import type { AuthStatus, AuthTokens, AuthUser } from './types';

export interface AuthContextValue {
  status: AuthStatus['status'];
  user: AuthUser | null;
  tokens: AuthTokens | null;
  /** 로그인 시작 (authorize URL 반환) */
  beginLogin: () => Promise<string>;
  /** 콜백 핸들러 */
  completeLogin: (params: { code: string; state: string }) => Promise<void>;
  /** 로그아웃 (URL 반환) */
  logout: () => Promise<string>;
  /** 토큰 강제 갱신 */
  refresh: () => Promise<AuthTokens | null>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export interface AuthProviderProps {
  client: AuthClient;
  /** 초기 토큰 (SSR 등) */
  initialTokens?: AuthTokens | null;
  children: ReactNode;
}

export function AuthProvider({ client, initialTokens = null, children }: AuthProviderProps) {
  const [tokens, setTokens] = useState<AuthTokens | null>(initialTokens);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus['status']>(
    initialTokens ? 'authenticated' : 'idle',
  );

  // 토큰 있으면 사용자 정보 조회
  useEffect(() => {
    let cancelled = false;
    if (tokens) {
      client
        .getUser()
        .then((u) => {
          if (!cancelled) {
            setUser(u);
            setStatus(u ? 'authenticated' : 'unauthenticated');
          }
        })
        .catch(() => !cancelled && setStatus('unauthenticated'));
    } else {
      setUser(null);
    }
    return () => {
      cancelled = true;
    };
  }, [tokens, client]);

  const beginLogin = useCallback(async () => {
    setStatus('authenticating');
    return client.beginLogin();
  }, [client]);

  const completeLogin = useCallback(
    async (params: { code: string; state: string }) => {
      const t = await client.completeLogin(params);
      setTokens(t);
    },
    [client],
  );

  const logout = useCallback(async () => {
    const url = await client.logout();
    setTokens(null);
    setUser(null);
    setStatus('unauthenticated');
    return url;
  }, [client]);

  const refresh = useCallback(async () => {
    const t = await client.refresh();
    setTokens(t);
    return t;
  }, [client]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, tokens, beginLogin, completeLogin, logout, refresh }),
    [status, user, tokens, beginLogin, completeLogin, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
