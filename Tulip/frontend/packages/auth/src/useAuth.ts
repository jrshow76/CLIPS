import { useContext } from 'react';

import { AuthContext, type AuthContextValue } from './context';

/**
 * 인증 상태·동작 hook.
 *
 * @throws AuthProvider 외부에서 호출 시
 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth는 <AuthProvider> 내부에서만 사용할 수 있습니다.');
  }
  return ctx;
}

/** 인증 여부만 빠르게 확인 */
export function useIsAuthenticated(): boolean {
  const { status } = useAuth();
  return status === 'authenticated';
}

/** 특정 scope 보유 여부 검사 */
export function useHasScope(scope: string): boolean {
  const { user } = useAuth();
  return user?.scopes.includes(scope) ?? false;
}

/** 특정 role 보유 여부 검사 */
export function useHasRole(role: string): boolean {
  const { user } = useAuth();
  return user?.roles.includes(role) ?? false;
}
