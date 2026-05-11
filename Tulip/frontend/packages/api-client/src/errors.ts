/**
 * Tulip+ API 표준 에러 클래스
 */
import type { ApiErrorResponse, ApiFieldError } from './types';

export class ApiError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly userMessage?: string;
  public readonly fieldErrors?: ApiFieldError[];
  public readonly traceId: string;
  public readonly debug?: Record<string, unknown>;
  public readonly raw?: ApiErrorResponse;

  constructor(args: {
    status: number;
    code: string;
    message: string;
    userMessage?: string;
    fieldErrors?: ApiFieldError[];
    traceId: string;
    debug?: Record<string, unknown>;
    raw?: ApiErrorResponse;
  }) {
    super(args.message);
    this.name = 'ApiError';
    this.status = args.status;
    this.code = args.code;
    this.userMessage = args.userMessage;
    this.fieldErrors = args.fieldErrors;
    this.traceId = args.traceId;
    this.debug = args.debug;
    this.raw = args.raw;
  }

  /** 인증 만료 (401) */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** 권한 없음 (403) */
  get isForbidden(): boolean {
    return this.status === 403;
  }

  /** 비즈니스 규칙 위반 (422) */
  get isBusinessError(): boolean {
    return this.status === 422;
  }

  /** 상태 충돌 (409) */
  get isConflict(): boolean {
    return this.status === 409;
  }

  /** Rate Limit (429) */
  get isRateLimited(): boolean {
    return this.status === 429;
  }
}

export class NetworkError extends Error {
  constructor(message: string, public readonly cause?: unknown) {
    super(message);
    this.name = 'NetworkError';
  }
}
