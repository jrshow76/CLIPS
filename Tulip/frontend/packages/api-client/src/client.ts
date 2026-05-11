/**
 * BaseClient — ofetch 기반 공통 HTTP 클라이언트
 *
 * 책임:
 * - 공통 헤더 (Authorization, X-Tenant-Id, X-Trace-Id, Accept-Language) 자동 첨부
 * - 응답 envelope 언래핑
 * - 에러 표준화 (ApiError)
 * - 토큰 401 시 refresh 훅 호출
 */
import {
  HEADER_BRANCH_ID,
  HEADER_IDEMPOTENCY_KEY,
  HEADER_TENANT_ID,
  HEADER_TRACE_ID,
} from '@tulip/config';
import { ofetch, type FetchOptions } from 'ofetch';

import { ApiError, NetworkError } from './errors';
import { generateTraceparent } from './trace';
import type { ApiResponse, RequestOptions } from './types';

export interface TokenProvider {
  /** 현재 access token (없으면 null) */
  getAccessToken: () => string | null | Promise<string | null>;
  /** 401 발생 시 호출 — 새 토큰 반환 또는 null */
  refresh?: () => Promise<string | null>;
  /** 인증 만료 강제 로그아웃 처리 */
  onUnauthorized?: () => void;
}

export interface TenantProvider {
  getTenantId: () => string | null;
  getBranchId?: () => string | null;
}

export interface BaseClientConfig {
  /** API base URL (예: https://api.tulip.example.com) */
  baseUrl: string;
  /** 기본 prefix (예: /api/v1) — 빈 문자열 가능 */
  basePath?: string;
  /** 토큰 제공자 */
  tokenProvider?: TokenProvider;
  /** 테넌트 제공자 */
  tenantProvider?: TenantProvider;
  /** Accept-Language */
  locale?: string;
  /** 기본 timeout (ms) */
  timeoutMs?: number;
  /** 디버그 모드 (서버 응답 debug 블록 노출) */
  debug?: boolean;
}

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

export class BaseClient {
  private readonly config: BaseClientConfig;
  private isRefreshing = false;
  private refreshPromise: Promise<string | null> | null = null;

  constructor(config: BaseClientConfig) {
    this.config = {
      basePath: '',
      locale: 'ko-KR',
      timeoutMs: 30_000,
      debug: false,
      ...config,
    };
  }

  /** GET */
  async get<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>('GET', path, options);
  }

  /** POST */
  async post<T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>('POST', path, { ...options, body });
  }

  /** PUT */
  async put<T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>('PUT', path, { ...options, body });
  }

  /** PATCH */
  async patch<T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>('PATCH', path, { ...options, body });
  }

  /** DELETE */
  async delete<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>('DELETE', path, options);
  }

  /**
   * 코어 request — 토큰 갱신·envelope 언래핑·에러 표준화.
   */
  async request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
    const url = this.buildUrl(path);
    const headers = await this.buildHeaders(method, options);

    const fetchOptions: FetchOptions = {
      method,
      headers,
      query: options.query,
      // ofetch는 객체를 JSON 직렬화한다 (Content-Type: application/json 자동).
      body: options.body as FetchOptions['body'],
      signal: options.signal,
      timeout: this.config.timeoutMs,
      retry: 0,
      // ofetch는 4xx/5xx에서도 응답 본문을 받아 throw — 우리는 직접 처리
      ignoreResponseError: true,
    };

    let res: Response;
    let payload: unknown;
    try {
      // ofetch.raw — Response + 본문 동시 접근
      const response = await ofetch.raw(url, fetchOptions);
      res = response as unknown as Response;
      payload = response._data;
    } catch (cause) {
      throw new NetworkError(`네트워크 오류: ${(cause as Error)?.message ?? 'unknown'}`, cause);
    }

    // 401 처리: refresh 시도 후 1회 재요청
    if (res.status === 401 && options.authenticated !== false && this.config.tokenProvider?.refresh) {
      const newToken = await this.tryRefresh();
      if (newToken) {
        return this.request<T>(method, path, options);
      }
      this.config.tokenProvider.onUnauthorized?.();
    }

    return this.handleEnvelope<T>(res, payload, options);
  }

  private handleEnvelope<T>(res: Response, payload: unknown, options: RequestOptions): T {
    const envelope = payload as ApiResponse<T> | undefined;

    if (!envelope || typeof envelope !== 'object') {
      // 204 No Content 등
      if (res.status === 204) return undefined as unknown as T;
      throw new ApiError({
        status: res.status,
        code: `HTTP-${res.status}`,
        message: `Unexpected response (${res.status})`,
        traceId: res.headers.get(HEADER_TRACE_ID) ?? '',
      });
    }

    if (envelope.success === false) {
      throw new ApiError({
        status: res.status,
        code: envelope.code,
        message: envelope.message,
        userMessage: envelope.userMessage,
        fieldErrors: envelope.fieldErrors,
        traceId: envelope.traceId,
        debug: this.config.debug ? envelope.debug : undefined,
        raw: envelope,
      });
    }

    // unwrap 기본 true — envelope.data 를 직접 반환
    if (options.unwrap === false) {
      return envelope as unknown as T;
    }
    return envelope.data as T;
  }

  private async buildHeaders(method: string, options: RequestOptions): Promise<Record<string, string>> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'Accept-Language': this.config.locale ?? 'ko-KR',
      [HEADER_TRACE_ID]: generateTraceparent(),
      ...options.headers,
    };

    if (!SAFE_METHODS.has(method) && options.body !== undefined) {
      headers['Content-Type'] = 'application/json; charset=utf-8';
    }

    // 인증
    if (options.authenticated !== false && this.config.tokenProvider) {
      const token = await this.config.tokenProvider.getAccessToken();
      if (token) headers.Authorization = `Bearer ${token}`;
    }

    // 테넌트·브랜치
    const tenantId = options.tenantId ?? this.config.tenantProvider?.getTenantId() ?? null;
    if (tenantId) headers[HEADER_TENANT_ID] = tenantId;
    const branchId = options.branchId ?? this.config.tenantProvider?.getBranchId?.() ?? null;
    if (branchId) headers[HEADER_BRANCH_ID] = branchId;

    // Idempotency
    if (options.idempotencyKey) {
      headers[HEADER_IDEMPOTENCY_KEY] = options.idempotencyKey;
    }

    return headers;
  }

  private buildUrl(path: string): string {
    const base = this.config.baseUrl.replace(/\/$/, '');
    const prefix = this.config.basePath ?? '';
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${base}${prefix}${normalizedPath}`;
  }

  private async tryRefresh(): Promise<string | null> {
    if (!this.config.tokenProvider?.refresh) return null;
    if (this.isRefreshing && this.refreshPromise) return this.refreshPromise;
    this.isRefreshing = true;
    this.refreshPromise = this.config.tokenProvider.refresh().finally(() => {
      this.isRefreshing = false;
      this.refreshPromise = null;
    });
    return this.refreshPromise;
  }
}

/**
 * 단일 전역 클라이언트 (앱에서 createClient → 주입 사용 권장)
 */
export function createApiClient(config: BaseClientConfig): BaseClient {
  return new BaseClient(config);
}
