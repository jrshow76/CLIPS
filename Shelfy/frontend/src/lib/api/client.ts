/**
 * Axios 인스턴스 및 인터셉터
 *
 * 역할:
 * - Access Token 자동 첨부 (요청 인터셉터)
 * - 401 응답 시 Refresh Token으로 갱신 후 원본 요청 재시도 (응답 인터셉터)
 * - 갱신 실패 시 인증 초기화 후 로그인 페이지로 리다이렉트
 *
 * 보안 원칙:
 * - Access Token은 Zustand 메모리 저장 (localStorage 금지)
 * - Refresh Token은 HttpOnly 쿠키로 서버 관리 (withCredentials: true)
 */

import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/authStore'
import type { ApiResponse } from '@/types/api'
import type { TokenRefreshResponse } from '@/types/auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL
if (!API_BASE_URL) {
  throw new Error('NEXT_PUBLIC_API_URL 환경변수가 설정되지 않았습니다.')
}

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Refresh Token 쿠키 자동 포함
})

// 요청 인터셉터: Access Token 자동 삽입
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const accessToken = useAuthStore.getState().accessToken
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

// 401 재시도 처리를 위한 플래그 타입 확장
interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

// 토큰 갱신 중복 요청 방지를 위한 Promise 캐시
let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = axios
    .post<ApiResponse<TokenRefreshResponse>>(
      `${API_BASE_URL}/auth/token/refresh`,
      {},
      { withCredentials: true }
    )
    .then((res) => {
      const data = res.data
      if (!data.success || !data.data) {
        throw new Error(data.error?.message ?? '토큰 갱신 실패')
      }
      return data.data.accessToken
    })
    .finally(() => {
      refreshPromise = null
    })

  return refreshPromise
}

// 응답 인터셉터: 401 시 토큰 갱신 후 재시도
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetryableConfig

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const newToken = await refreshAccessToken()
        useAuthStore.getState().setAccessToken(newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return apiClient(originalRequest)
      } catch {
        useAuthStore.getState().clearAuth()
        // 브라우저 환경에서만 리다이렉트
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
