/**
 * 사용자/프로필 API 함수 모음
 * API 요구사항 정의서 7. 사용자 프로필 API 기반
 */

import apiClient from './client'
import type { ApiResponse } from '@/types/api'
import type { MyProfile, UpdateProfileRequest } from '@/types/user'

export interface ChangePasswordRequest {
  currentPassword: string
  newPassword: string
  newPasswordConfirm: string
}

export interface ChangePasswordResponse {
  message: string
}

export interface UserWithdrawRequest {
  password: string
  reason?: string
}

export interface WithdrawResponse {
  message: string
  withdrawnAt: string
}

/** 내 프로필 조회 (인증 필요) */
export async function fetchMyProfile(): Promise<MyProfile> {
  const res = await apiClient.get<ApiResponse<MyProfile>>('/users/me')
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '프로필 조회에 실패했습니다.')
  }
  return res.data.data
}

/** 내 프로필 수정 (인증 필요) */
export async function updateProfile(
  request: UpdateProfileRequest
): Promise<MyProfile> {
  const res = await apiClient.patch<ApiResponse<MyProfile>>(
    '/users/me',
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '프로필 수정에 실패했습니다.')
  }
  return res.data.data
}

/** 비밀번호 변경 (인증 필요) */
export async function changePassword(
  request: ChangePasswordRequest
): Promise<ChangePasswordResponse> {
  const res = await apiClient.post<ApiResponse<ChangePasswordResponse>>(
    '/users/me/password',
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '비밀번호 변경에 실패했습니다.')
  }
  return res.data.data
}

/** 회원 탈퇴 (인증 필요) */
export async function withdraw(
  request: UserWithdrawRequest
): Promise<WithdrawResponse> {
  const res = await apiClient.post<ApiResponse<WithdrawResponse>>(
    '/users/me/withdraw',
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '회원 탈퇴에 실패했습니다.')
  }
  return res.data.data
}
