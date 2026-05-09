/**
 * 인증 상태 훅
 *
 * 제공 기능:
 * - 로그인 여부 및 사용자 정보 접근
 * - 로그인/로그아웃 액션 (API 호출 + 스토어 업데이트)
 * - 인증 필요 페이지 리다이렉트
 */

'use client'

import { useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/authStore'
import { login as loginApi, logout as logoutApi } from '@/lib/api/auth'
import type { LoginRequest } from '@/types/auth'
import type { AuthUser } from '@/types/auth'

export function useAuth() {
  const router = useRouter()
  const { accessToken, user, setAuth, clearAuth } = useAuthStore()

  const isLoggedIn = accessToken !== null

  /**
   * 로그인 처리
   * 성공 시 Access Token + 사용자 정보를 스토어에 저장
   * 사용자 정보는 loginResponse 데이터가 없으므로 별도 me API 호출 필요 시 확장
   */
  const login = useCallback(
    async (request: LoginRequest) => {
      const response = await loginApi(request)
      // 로그인 응답에는 토큰만 포함. 사용자 정보는 /users/me 에서 별도 조회 필요.
      // 여기서는 임시 AuthUser를 구성하고, 이후 me API 호출로 보완한다.
      // 실제 구현 시 로그인 후 /users/me 를 호출하여 전체 사용자 정보를 채운다.
      const partialUser: AuthUser = {
        userId: 0,
        email: request.email,
        nickname: '',
        emailVerified: false,
      }
      setAuth(response.accessToken, partialUser)
    },
    [setAuth]
  )

  /**
   * 로그아웃 처리
   * API 호출 후 스토어 초기화, 홈으로 리다이렉트
   */
  const logout = useCallback(async () => {
    try {
      await logoutApi()
    } finally {
      clearAuth()
      router.push('/')
    }
  }, [clearAuth, router])

  /**
   * 인증 필요 페이지 가드
   * 비로그인 상태에서 호출 시 로그인 페이지로 리다이렉트
   */
  const requireAuth = useCallback(
    (redirectPath?: string) => {
      if (!isLoggedIn) {
        const returnUrl = redirectPath ?? window.location.pathname
        router.push(`/login?returnUrl=${encodeURIComponent(returnUrl)}`)
        return false
      }
      return true
    },
    [isLoggedIn, router]
  )

  /**
   * 사용자 정보 업데이트 (외부에서 user를 직접 주입할 때 사용)
   */
  const updateUser = useCallback(
    (updatedUser: AuthUser) => {
      useAuthStore.getState().setUser(updatedUser)
    },
    []
  )

  return {
    isLoggedIn,
    user,
    login,
    logout,
    requireAuth,
    updateUser,
  }
}
