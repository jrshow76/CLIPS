/**
 * 인증 도메인 타입 정의
 * API 요구사항 정의서 2. 인증 API 기반
 */

/** 회원가입 요청 */
export interface SignupRequest {
  email: string
  password: string
  passwordConfirm: string
  nickname: string
  agreeTerms: boolean
  agreePrivacy: boolean
  agreeMarketing: boolean
}

/** 회원가입 응답 */
export interface SignupResponse {
  userId: number
  email: string
  nickname: string
}

/** 로그인 요청 */
export interface LoginRequest {
  email: string
  password: string
}

/** 로그인 응답 (Access Token은 메모리 저장, Refresh Token은 HttpOnly 쿠키) */
export interface LoginResponse {
  accessToken: string
  tokenType: string
  expiresIn: number
}

/** Access Token 갱신 응답 */
export interface TokenRefreshResponse {
  accessToken: string
  tokenType: string
  expiresIn: number
}

/** 비밀번호 재설정 요청 */
export interface ForgotPasswordRequest {
  email: string
}

/** 비밀번호 재설정 */
export interface ResetPasswordRequest {
  token: string
  newPassword: string
  newPasswordConfirm: string
}

/** 회원 탈퇴 요청 */
export interface WithdrawRequest {
  password: string
}

/** Zustand authStore에서 관리하는 사용자 정보 */
export interface AuthUser {
  userId: number
  email: string
  nickname: string
  profileImageUrl?: string
  emailVerified: boolean
}
