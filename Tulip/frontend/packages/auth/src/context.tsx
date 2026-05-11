/**
 * AuthProvider — React Context 기반 인증 상태 관리 (Phase 1-B / BFF 패턴)
 *
 * 동작:
 * 1. Mount 시 `client.me()` 호출하여 세션 복원
 *    - 200 → user 채움, status='authenticated'
 *    - 401 → status='unauthenticated' (익명 라우트는 계속 사용 가능)
 * 2. `login(returnUri)` — `client.initiateLogin` 호출 후 받은 URL로 redirect
 * 3. `handleCallback({code, state})` — 콜백 라우트에서 호출, 토큰 저장 + user 갱신
 * 4. `logout()` — 서버 호출 + 메모리 토큰 폐기 + status 초기화
 * 5. access token 만료 60초 전 자동 refresh 타이머
 */
'use client';

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import { type AuthClient } from './client';
import type { AuthStatus, AuthTokens, AuthUser, LoginCallbackResponse } from './types';

export interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** 로그인 시작 — 콜백 절대 URL을 전달하면 IdP로 redirect */
  login: (returnUri: string, tenantHint?: string) => Promise<void>;
  /** 콜백 라우트에서 호출 — code/state로 토큰 교환 */
  handleCallback: (params: { code: string; state: string }) => Promise<LoginCallbackResponse>;
  /** 로그아웃 — 메모리 토큰 폐기 + 서버 쿠키 무효화 */
  logout: () => Promise<void>;
  /** 토큰 강제 갱신 */
  refresh: () => Promise<AuthTokens | null>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export interface AuthProviderProps {
  client: AuthClient;
  /** SSR 등에서 미리 알고 있는 사용자 정보 */
  initialUser?: AuthUser | null;
  /** Mount 시 /me 호출 비활성화 (테스트용) */
  skipBootstrap?: boolean;
  children: ReactNode;
}

/** access token 만료 몇 ms 전에 refresh 할지 */
const REFRESH_BUFFER_MS = 60 * 1000;

export function AuthProvider({
  client,
  initialUser = null,
  skipBootstrap = false,
  children,
}: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(initialUser);
  const [accessToken, setAccessToken] = useState<string | null>(
    client.getAccessToken(),
  );
  const [status, setStatus] = useState<AuthStatus>(initialUser ? 'authenticated' : 'idle');

  /** 자동 refresh 타이머 핸들 */
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** 토큰 저장소 구독 → React state 동기화 */
  useEffect(() => {
    return client.getStorage().subscribe((tokens) => {
      setAccessToken(tokens?.accessToken ?? null);
      scheduleRefresh(tokens);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client]);

  /** Mount 시 세션 복원: /me 호출 */
  useEffect(() => {
    if (skipBootstrap) return;
    let cancelled = false;
    setStatus('loading');
    client
      .me()
      .then((u) => {
        if (cancelled) return;
        if (u) {
          setUser(u);
          setStatus('authenticated');
        } else {
          // 401 — 익명 상태. refresh 쿠키가 있을 수 있으니 한번 시도.
          client
            .refresh()
            .then((tokens) => {
              if (cancelled) return;
              if (tokens) {
                return client.me().then((u2) => {
                  if (cancelled) return;
                  if (u2) {
                    setUser(u2);
                    setStatus('authenticated');
                  } else {
                    setStatus('unauthenticated');
                  }
                });
              }
              setStatus('unauthenticated');
              return undefined;
            })
            .catch(() => !cancelled && setStatus('unauthenticated'));
        }
      })
      .catch(() => !cancelled && setStatus('error'));
    return () => {
      cancelled = true;
    };
  }, [client, skipBootstrap]);

  /** 자동 refresh 스케줄링 */
  const scheduleRefresh = useCallback(
    (tokens: AuthTokens | null) => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
      if (!tokens) return;
      const delay = Math.max(0, tokens.expiresAt - Date.now() - REFRESH_BUFFER_MS);
      refreshTimerRef.current = setTimeout(() => {
        void client.refresh().catch(() => {
          // refresh 실패 → 미인증 상태
          setUser(null);
          setStatus('unauthenticated');
        });
      }, delay);
    },
    [client],
  );

  // Unmount 시 타이머 정리
  useEffect(() => {
    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, []);

  const login = useCallback(
    async (returnUri: string, tenantHint?: string) => {
      setStatus('loading');
      const result = await client.initiateLogin(returnUri, tenantHint);
      if (typeof window !== 'undefined') {
        window.location.assign(result.authorizationUrl);
      }
    },
    [client],
  );

  const handleCallback = useCallback(
    async (params: { code: string; state: string }) => {
      const result = await client.handleCallback(params.code, params.state);
      setUser(result.user);
      setStatus('authenticated');
      return result;
    },
    [client],
  );

  const logout = useCallback(async () => {
    await client.logout();
    setUser(null);
    setStatus('unauthenticated');
  }, [client]);

  const refresh = useCallback(async () => {
    const t = await client.refresh();
    if (!t) {
      setUser(null);
      setStatus('unauthenticated');
    }
    return t;
  }, [client]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      accessToken,
      isAuthenticated: status === 'authenticated' && !!user,
      isLoading: status === 'loading' || status === 'idle',
      login,
      handleCallback,
      logout,
      refresh,
    }),
    [status, user, accessToken, login, handleCallback, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
