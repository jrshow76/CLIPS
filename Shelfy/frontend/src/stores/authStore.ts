/**
 * 인증 상태 전역 스토어 (Zustand)
 *
 * 저장 원칙:
 * - accessToken: 메모리(Zustand) 저장 — XSS 방어 목적, localStorage 절대 금지
 * - refreshToken: HttpOnly 쿠키로 서버 관리, 클라이언트에서 접근 불가
 * - user 정보: Zustand 메모리 저장 (탭 새로고침 시 API 재조회)
 */

import { create } from 'zustand'
import type { AuthUser } from '@/types/auth'

interface AuthState {
  /** 메모리에만 저장하는 Access Token */
  accessToken: string | null
  /** 인증된 사용자 정보 */
  user: AuthUser | null
  /** 초기 인증 상태 확인 완료 여부 */
  isInitialized: boolean
}

interface AuthActions {
  /** 로그인 성공 시 토큰 + 사용자 정보 저장 */
  setAuth: (accessToken: string, user: AuthUser) => void
  /** 토큰 갱신 시 Access Token만 교체 */
  setAccessToken: (accessToken: string) => void
  /** 사용자 정보 업데이트 (프로필 수정 후) */
  setUser: (user: AuthUser) => void
  /** 로그아웃/세션 만료 시 전체 초기화 */
  clearAuth: () => void
  /** 앱 초기 렌더링 완료 표시 */
  setInitialized: () => void
}

export const useAuthStore = create<AuthState & AuthActions>((set) => ({
  // 초기 상태
  accessToken: null,
  user: null,
  isInitialized: false,

  // 액션
  setAuth: (accessToken, user) => set({ accessToken, user }),

  setAccessToken: (accessToken) => set({ accessToken }),

  setUser: (user) => set({ user }),

  clearAuth: () => set({ accessToken: null, user: null }),

  setInitialized: () => set({ isInitialized: true }),
}))

/** 로그인 여부 선택자 (불필요한 리렌더링 방지) */
export const selectIsLoggedIn = (state: AuthState) => state.accessToken !== null

/** 사용자 정보 선택자 */
export const selectUser = (state: AuthState) => state.user
