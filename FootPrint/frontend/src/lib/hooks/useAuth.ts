'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { authApi, type LoginRequest, type SignupRequest } from '@/lib/api/auth';
import { useAuthStore } from '@/store/authStore';

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setUser, clearAuth } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: async (res) => {
      const { accessToken, refreshToken } = res.data.data!;
      localStorage.setItem('accessToken', accessToken);
      localStorage.setItem('refreshToken', refreshToken);
      // 토큰 저장 후 사용자 정보 조회
      const meRes = await authApi.me();
      if (meRes.data.data) setUser(meRes.data.data);
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      router.push('/map');
    },
  });

  const signupMutation = useMutation({
    mutationFn: (data: SignupRequest) => authApi.signup(data),
    onSuccess: () => {
      router.push('/login');
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: () => {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      clearAuth();
      queryClient.clear();
      router.push('/login');
    },
  });

  return {
    loginMutation,
    signupMutation,
    logoutMutation,
  };
}

export function useMe() {
  const { setUser, isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const res = await authApi.me();
      if (res.data.data) {
        setUser(res.data.data);
      }
      return res.data.data;
    },
    enabled: typeof window !== 'undefined' && !!localStorage.getItem('accessToken'),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
