import { ERROR_MESSAGES } from '@/lib/constants';
import type { ApiErrorPayload } from '@/types/api';

/**
 * AppError: API 응답의 `success: false` 또는 네트워크 오류를 통합 표현.
 * - 컴포넌트는 `error.code`, `error.userMessage`를 직접 사용.
 */
export class AppError extends Error {
  public readonly code: string;
  public readonly userMessage: string;
  public readonly status: number;
  public readonly details?: Record<string, unknown>;
  public readonly traceId?: string;

  constructor(payload: {
    code: string;
    message?: string;
    status?: number;
    details?: Record<string, unknown>;
    traceId?: string;
  }) {
    const userMsg = ERROR_MESSAGES[payload.code] ?? payload.message ?? '알 수 없는 오류가 발생했습니다.';
    super(userMsg);
    this.name = 'AppError';
    this.code = payload.code;
    this.userMessage = userMsg;
    this.status = payload.status ?? 500;
    this.details = payload.details;
    this.traceId = payload.traceId;
  }

  static fromApi(payload: ApiErrorPayload, status: number): AppError {
    return new AppError({
      code: payload.code,
      message: payload.message,
      status,
      details: payload.details,
      traceId: payload.trace_id,
    });
  }

  static network(message = '네트워크 오류가 발생했습니다.'): AppError {
    return new AppError({ code: 'E_NETWORK', message, status: 0 });
  }
}

/**
 * 필드 검증 오류(E0003)에서 RHF가 사용할 수 있는 형태로 변환.
 */
export function extractFieldErrors(err: AppError): Record<string, string> | null {
  if (err.code !== 'E0003' || !err.details) return null;
  const result: Record<string, string> = {};
  for (const [key, val] of Object.entries(err.details)) {
    if (Array.isArray(val)) result[key] = String(val[0] ?? '');
    else if (typeof val === 'string') result[key] = val;
  }
  return Object.keys(result).length > 0 ? result : null;
}
