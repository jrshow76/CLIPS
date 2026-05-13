import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';
import { v4 as uuid } from 'uuid';

import { session } from '@/lib/auth/session';
import { AppError } from '@/lib/api/error';
import { useTradeModeStore } from '@/stores/trade-mode-store';
import type { ApiResponse, ApiSuccess, TradeMode } from '@/types/api';

/**
 * Axios 인스턴스.
 *
 * 인터셉터 책임:
 *  - 요청: Authorization, X-Trade-Mode, X-Idempotency-Key, X-Request-Id 자동 부착
 *  - 응답: { success, data | error } envelope 처리 → 실패 시 AppError throw
 *  - 401 + E0001 발생 시 refresh 토큰으로 1회 자동 재시도
 *
 * docs/22_frontend_structure.md §5, docs/24_api_response_spec.md §4~§5 참조.
 */

declare module 'axios' {
  export interface AxiosRequestConfig {
    /** X-Trade-Mode 헤더 자동 주입 여부 (주문/모드 API) */
    requireTradeMode?: boolean;
    /** 멱등성 키 자동 발급 (POST /orders 등) */
    idempotent?: boolean;
    /** 401 재시도 락 */
    __retried?: boolean;
  }
  export interface InternalAxiosRequestConfig {
    /** X-Trade-Mode 헤더 자동 주입 여부 (주문/모드 API) */
    requireTradeMode?: boolean;
    /** 멱등성 키 자동 발급 (POST /orders 등) */
    idempotent?: boolean;
    /** 401 재시도 락 */
    __retried?: boolean;
  }
}

const baseURL =
  process.env.NEXT_PUBLIC_API_BASE_URL && process.env.NEXT_PUBLIC_API_BASE_URL.length > 0
    ? `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1`
    : '/api/v1';

export const apiClient: AxiosInstance = axios.create({
  baseURL,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
});

/* ============================================================
 *  Request interceptor
 * ============================================================ */
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const tokens = session.get();
  if (tokens?.access_token) {
    config.headers.set('Authorization', `Bearer ${tokens.access_token}`);
  }

  // X-Request-Id : 클라이언트 trace_id
  const tracePrefix = process.env.NEXT_PUBLIC_TRACE_PREFIX ?? 'tp-web';
  if (!config.headers.has('X-Request-Id')) {
    config.headers.set('X-Request-Id', `${tracePrefix}-${uuid()}`);
  }

  // X-Trade-Mode
  if (config.requireTradeMode) {
    const mode: TradeMode = useTradeModeStore.getState().mode;
    config.headers.set('X-Trade-Mode', mode);
  }

  // X-Idempotency-Key (자동 발급) — 호출 측에서 별도 지정한 경우 우선
  if (config.idempotent && !config.headers.has('X-Idempotency-Key')) {
    config.headers.set('X-Idempotency-Key', uuid());
  }

  return config;
});

/* ============================================================
 *  Response interceptor
 *   - 표준 envelope 해석
 *   - 401 자동 refresh
 * ============================================================ */
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;
  const tokens = session.get();
  if (!tokens?.refresh_token) throw AppError.fromApi({ code: 'E0001', message: '세션 만료' }, 401);
  refreshPromise = axios
    .post<ApiResponse<{ access_token: string; expires_in: number }>>(
      `${baseURL}/auth/refresh`,
      { refresh_token: tokens.refresh_token },
      { timeout: 8000 },
    )
    .then((res) => {
      if (!res.data.success) throw AppError.fromApi(res.data.error, res.status);
      session.set({
        access_token: res.data.data.access_token,
        refresh_token: tokens.refresh_token,
        expires_in: res.data.data.expires_in,
      });
      return res.data.data.access_token;
    })
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError<ApiResponse<unknown>>) => {
    const config = error.config as InternalAxiosRequestConfig | undefined;
    const status = error.response?.status ?? 0;
    const data = error.response?.data;

    // 401 + E0001 → refresh 후 1회 재시도
    const isAuthError =
      status === 401 && data && !data.success && data.error.code === 'E0001' && !config?.__retried;
    if (isAuthError && config) {
      try {
        const newToken = await refreshAccessToken();
        config.__retried = true;
        config.headers.set('Authorization', `Bearer ${newToken}`);
        return apiClient.request(config);
      } catch (refreshErr) {
        session.clear();
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        throw refreshErr;
      }
    }

    if (data && !data.success) {
      throw AppError.fromApi(data.error, status);
    }
    throw AppError.network(error.message);
  },
);

/* ============================================================
 *  Helper: envelope 해석 (성공 시 data 만 반환)
 * ============================================================ */
export async function apiRequest<T>(config: AxiosRequestConfig): Promise<T> {
  const res = await apiClient.request<ApiResponse<T>>(config);
  const body = res.data;
  if (!body.success) {
    throw AppError.fromApi(body.error, res.status);
  }
  return (body as ApiSuccess<T>).data;
}

export const api = {
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    apiRequest<T>({ ...config, url, method: 'GET' }),
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    apiRequest<T>({ ...config, url, method: 'POST', data }),
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    apiRequest<T>({ ...config, url, method: 'PATCH', data }),
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    apiRequest<T>({ ...config, url, method: 'PUT', data }),
  delete: <T>(url: string, config?: AxiosRequestConfig) =>
    apiRequest<T>({ ...config, url, method: 'DELETE' }),
};
