/**
 * TradePilot 공통 API 응답 타입.
 * docs/24_api_response_spec.md §2 참조.
 */

export type TradeMode = 'SIM' | 'LIVE';

export interface ApiSuccess<T> {
  success: true;
  data: T;
}

export interface ApiErrorPayload {
  code: string; // E0001 ~ E0099
  message: string;
  details?: Record<string, unknown>;
  trace_id?: string;
  ts?: string;
}

export interface ApiFailure {
  success: false;
  error: ApiErrorPayload;
}

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure;

export interface PageResponse<T> {
  items: T[];
  page: number;
  size: number;
  total: number | null;
  has_next: boolean;
}

export interface JobAccepted {
  job_id: string;
  status: 'QUEUED' | 'RUNNING' | 'DONE' | 'FAILED';
}

export interface SortSpec<F extends string = string> {
  field: F;
  direction: 'asc' | 'desc';
}

export interface PageQuery {
  page?: number;
  size?: number;
  sort?: string | string[];
}
