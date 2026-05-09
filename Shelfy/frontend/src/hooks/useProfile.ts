/**
 * 사용자 프로필 TanStack Query 훅 모음
 * DevLead 개발 표준 6.4 TanStack Query 사용 규칙 기반
 */

'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchMyProfile,
  updateProfile,
  changePassword,
  withdraw,
} from '@/lib/api/users'
import type { UpdateProfileRequest } from '@/types/user'
import type {
  ChangePasswordRequest,
  UserWithdrawRequest,
} from '@/lib/api/users'
import { useAuth } from './useAuth'

// Query Key 상수화 (캐시 무효화 일관성 확보)
export const profileQueryKeys = {
  all: ['profile'] as const,
  my: () => [...profileQueryKeys.all, 'me'] as const,
} as const

/** 내 프로필 조회 */
export function useMyProfile() {
  const { isLoggedIn } = useAuth()

  return useQuery({
    queryKey: profileQueryKeys.my(),
    queryFn: fetchMyProfile,
    enabled: isLoggedIn,
    staleTime: 5 * 60 * 1000, // 5분
  })
}

/** 내 프로필 수정 뮤테이션 */
export function useUpdateProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: UpdateProfileRequest) => updateProfile(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileQueryKeys.my() })
    },
  })
}

/** 비밀번호 변경 뮤테이션 */
export function useChangePassword() {
  return useMutation({
    mutationFn: (request: ChangePasswordRequest) => changePassword(request),
  })
}

/** 회원 탈퇴 뮤테이션 */
export function useWithdraw() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: UserWithdrawRequest) => withdraw(request),
    onSuccess: () => {
      // 탈퇴 성공 시 캐시 전체 초기화
      queryClient.clear()
    },
  })
}
