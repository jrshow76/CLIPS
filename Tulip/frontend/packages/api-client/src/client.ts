/**
 * BaseClient — ofetch 기반 공통 HTTP 클라이언트
 *
 * 책임:
 * - 공통 헤더 (Authorization, X-Tenant-Id, X-Trace-Id, Accept-Language) 자동 첨부
 * - 응답 envelope 언래핑
 * - 에러 표준화 (ApiError)
 * - 토큰 401 시 single-flight refresh 핸들러 호출 후 1회 재시도
 *
 * refresh 핸들러는 `@tulip/auth`(또는 동등 구현)에서 `setRefreshHandler`로
 * 주입한다. 패키지 간 의존 순환 회피를 위해 setter 기반 lazy 연결.
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
  /** 인증 만료 강제 로그아웃 처리 (refresh 실패 시 호출) */
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
  /** 인증 자격증명 송수신 (HttpOnly refresh 쿠키 등) */
  withCredentials?: boolean;
}

/**
 * 401 발생 시 호출되는 refresh 핸들러.
 *
 * - 새 access token을 반환하면 BaseClient가 원 요청을 재시도한다.
 * - null을 반환하면 `tokenProvider.onUnauthorized` 호출 후 401을 그대로 throw.
 */
export type RefreshHandler = () => Promise<string | null>;

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

export class BaseClient {
  private readonly config: BaseClientConfig;
  private isRefreshing = false;
  private refreshPromise: Promise<string | null> | null = null;
  /** 외부에서 주입되는 refresh 핸들러 (단일 인스턴스 공유 가정) */
  private refreshHandler: RefreshHandler | null = null;

  constructor(config: BaseClientConfig) {
    this.config = {
      basePath: '',
      locale: 'ko-KR',
      timeoutMs: 30_000,
      debug: false,
      withCredentials: true,
      ...config,
    };
  }

  /**
   * refresh 핸들러 주입.
   *
   * 일반적으로 `@tulip/auth.AuthClient`의 `refresh`를 어댑터로 감싸 등록한다:
   * ```ts
   * apiClient.setRefreshHandler(async () => {
   *   const t = await authClient.refresh();
   *   return t?.accessToken ?? null;
   * });
   * ```
   */
  setRefreshHandler(handler: RefreshHandler | null): void {
    this.refreshHandler = handler;
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
    return this.requestInternal<T>(method, path, options, /* retried */ false);
  }

  private async requestInternal<T>(
    method: string,
    path: string,
    options: RequestOptions,
    retried: boolean,
  ): Promise<T> {
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
      // HttpOnly refresh 쿠키 송수신
      credentials: this.config.withCredentials ? 'include' : 'same-origin',
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

    // 401 처리: refresh 시도 후 1회 재요청 (single-flight)
    if (res.status === 401 && options.authenticated !== false && !retried && this.refreshHandler) {
      const newToken = await this.tryRefresh();
      if (newToken) {
        return this.requestInternal<T>(method, path, options, /* retried */ true);
      }
      this.config.tokenProvider?.onUnauthorized?.();
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

  /**
   * single-flight refresh — 동시에 여러 요청이 401을 받아도
   * refresh는 한 번만 실행되고, 결과를 공유한다.
   */
  private async tryRefresh(): Promise<string | null> {
    if (!this.refreshHandler) return null;
    if (this.isRefreshing && this.refreshPromise) return this.refreshPromise;
    this.isRefreshing = true;
    this.refreshPromise = this.refreshHandler().finally(() => {
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
