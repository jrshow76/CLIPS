/**
 * Tulip+ API 표준 응답 envelope (DEV-03 §4)
 */

export interface ApiPageMetaOffset {
  type: 'offset';
  number: number;
  size: number;
  totalElements: number;
  totalPages: number;
}

export interface ApiPageMetaCursor {
  type: 'cursor';
  limit: number;
  next?: string | null;
}

export type ApiPageMeta = ApiPageMetaOffset | ApiPageMetaCursor;

export interface ApiMeta {
  tenantId?: string;
  branchId?: string;
  page?: ApiPageMeta;
  sort?: string[];
  filter?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ApiFieldError {
  field: string;
  message: string;
  rejectedValue?: unknown;
}

export interface ApiSuccessResponse<T> {
  success: true;
  code: 'OK' | string;
  message?: string;
  userMessage?: string;
  data: T;
  meta?: ApiMeta;
  timestamp: string;
  traceId: string;
}

export interface ApiErrorResponse {
  success: false;
  code: string;
  message: string;
  userMessage?: string;
  fieldErrors?: ApiFieldError[];
  debug?: Record<string, unknown>;
  timestamp: string;
  traceId: string;
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

/**
 * 페이지네이션 응답 헬퍼
 */
export interface ApiOffsetPage<T> {
  items: T[];
  page: ApiPageMetaOffset;
}

export interface ApiCursorPage<T> {
  items: T[];
  cursor: ApiPageMetaCursor;
}

export interface RequestOptions {
  /** 인증 토큰 자동 첨부 여부 */
  authenticated?: boolean;
  /** 특정 테넌트 ID 강제 (Platform admin 한정) */
  tenantId?: string;
  /** 브랜치 컨텍스트 */
  branchId?: string;
  /** Idempotency-Key (POST 멱등성) */
  idempotencyKey?: string;
  /** 추가 헤더 */
  headers?: Record<string, string>;
  /** 쿼리 파라미터 */
  query?: Record<string, unknown>;
  /** 본문 (POST/PUT/PATCH) */
  body?: unknown;
  /** AbortSignal */
  signal?: AbortSignal;
  /** 응답 envelope 언래핑 여부 (true 기본) */
  unwrap?: boolean;
}
