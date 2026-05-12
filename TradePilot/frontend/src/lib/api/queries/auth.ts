import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { session } from '@/lib/auth/session';
import { useAuthStore } from '@/stores/auth-store';
import { useTradeModeStore } from '@/stores/trade-mode-store';
import type { AuthTokens, LoginRequest, SignupRequest, User } from '@/types/user';

import { USE_MOCK, mockDelay } from './_mock-helpers';
import { mockUser } from '@/lib/mocks/data';

/** 현재 사용자 조회 */
export function useMe() {
  return useQuery<User>({
    queryKey: queryKeys.auth.me(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockUser);
      return api.get<User>('/users/me');
    },
    staleTime: 5 * 60 * 1000,
  });
}

/** 로그인 mutation */
export function useLogin() {
  const qc = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  const setMode = useTradeModeStore((s) => s.setMode);

  return useMutation({
    mutationFn: async (payload: LoginRequest) => {
      if (USE_MOCK) {
        return mockDelay<AuthTokens & { user: User }>({
          access_token: 'mock.access.token',
          refresh_token: 'mock.refresh.token',
          expires_in: 1800,
          user: mockUser,
        });
      }
      const tokens = await api.post<AuthTokens>('/auth/login', payload);
      session.set(tokens);
      const me = await api.get<User>('/users/me');
      return { ...tokens, user: me };
    },
    onSuccess: (data) => {
      session.set({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        expires_in: data.expires_in,
      });
      setUser(data.user);
      setMode(data.user.trade_mode, { confirmed: true });
      qc.invalidateQueries({ queryKey: queryKeys.auth.me() });
    },
  });
}

/** 회원가입 */
export function useSignup() {
  return useMutation({
    mutationFn: async (payload: SignupRequest) => {
      if (USE_MOCK) return mockDelay({ user_id: 'usr_mock', status: 'PENDING_VERIFY' as const });
      return api.post<{ user_id: string; status: string }>('/auth/signup', payload);
    },
  });
}

/** 로그아웃 */
export function useLogout() {
  const reset = useAuthStore((s) => s.reset);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (!USE_MOCK) await api.post<{ logged_out: boolean }>('/auth/logout');
      session.clear();
    },
    onSettled: () => {
      reset();
      qc.clear();
    },
  });
}
