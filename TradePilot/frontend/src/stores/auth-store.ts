import { create } from 'zustand';

import type { User } from '@/types/user';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  reset: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setLoading: (loading) => set({ isLoading: loading }),
  reset: () => set({ user: null, isAuthenticated: false, isLoading: false }),
}));

/** 권한 헬퍼 (도메인 분리: 라우트 가드 / 메뉴 노출) */
export function hasRole(user: User | null, ...roles: string[]): boolean {
  if (!user) return false;
  return roles.includes(user.role);
}

export function canTradeLive(user: User | null): boolean {
  if (!user) return false;
  return user.role === 'ROLE_TRADER_PRO' || user.role === 'ROLE_ADMIN';
}
