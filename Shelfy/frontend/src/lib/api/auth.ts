/**
 * 인증 API 함수 모음
 * API 요구사항 정의서 2. 인증 API 기반
 */

import apiClient from './client'
import type { ApiResponse } from '@/types/api'
import type {
  SignupRequest,
  SignupResponse,
  LoginRequest,
  LoginResponse,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  WithdrawRequest,
} from '@/types/auth'

/** 회원가입 */
export async function signup(request: SignupRequest): Promise<SignupResponse> {
  const res = await apiClient.post<ApiResponse<SignupResponse>>(
    '/auth/signup',
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '회원가입에 실패했습니다.')
  }
  return res.data.data
}

/** 로그인 */
export async function login(request: LoginRequest): Promise<LoginResponse> {
  const res = await apiClient.post<ApiResponse<LoginResponse>>(
    '/auth/login',
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '로그인에 실패했습니다.')
  }
  return res.data.data
}

/** 로그아웃 (204 No Content) */
export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}

/** 이메일 인증 재발송 */
export async function resendVerification(email: string): Promise<{ message: string }> {
  const res = await apiClient.post<ApiResponse<{ message: string }>>(
    '/auth/resend-verification',
    { email }
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '재발송에 실패했습니다.')
  }
  return res.data.data
}

/** 비밀번호 재설정 요청 */
export async function forgotPassword(
  request: ForgotPasswordRequest
): Promise<{ message: string }> {
  const res = await apiClient.post<ApiResponse<{ message: string }>>(
    '/auth/forgot-password',
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '요청에 실패했습니다.')
  }
  return res.data.data
}

/** 비밀번호 재설정 */
export async function resetPassword(
  request: ResetPasswordRequest
): Promise<{ message: string }> {
  const res = await apiClient.post<ApiResponse<{ message: string }>>(
    '/auth/reset-password',
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '비밀번호 재설정에 실패했습니다.')
  }
  return res.data.data
}

/** 회원 탈퇴 (204 No Content) */
export async function withdraw(request: WithdrawRequest): Promise<void> {
  await apiClient.delete('/auth/me', { data: request })
}
