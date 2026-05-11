/**
 * AuthClient — iam-service `/api/v1/auth/*` 위임 클라이언트 (Phase 1-B / BFF 패턴)
 *
 * 본 클라이언트는 PKCE state/verifier를 직접 보관하지 않는다.
 * iam-service가 세션 저장소(Redis 등)에 보관·검증한 뒤 access token만 응답한다.
 *
 * - 응답 envelope: `{ success, code, data, ... }` (DEV-03 §4)
 * - refresh token: HttpOnly Secure 쿠키 → `credentials: 'include'`
 * - access token: 메모리 보관 (AuthStorage)
 */
import { createMemoryStorage, type AuthStorage } from './storage';
import type {
  AuthClientConfig,
  AuthTokens,
  AuthUser,
  LoginCallbackRequest,
  LoginCallbackResponse,
  LoginInitiateRequest,
  LoginInitiateResponse,
  RefreshResponse,
} from './types';

/** ApiResponse envelope (api-client/types와 동일 구조; 의존 순환 회피 위해 로컬 선언) */
interface ApiEnvelope<T> {
  success: boolean;
  code: string;
  message?: string;
  userMessage?: string;
  data?: T;
  fieldErrors?: Array<{ field: string; message: string }>;
  timestamp?: string;
  traceId?: string;
}

export interface AuthClientOptions {
  config: AuthClientConfig;
  storage?: AuthStorage;
  /** fetch 구현 주입 — SSR/테스트용. 기본은 globalThis.fetch */
  fetchImpl?: typeof fetch;
}

const DEFAULT_BASE_PATH = '/api/v1/auth';

/**
 * iam-service `/api/v1/auth/*` 엔드포인트 wrapper.
 *
 * NOTE: 본 클라이언트는 단순 fetch를 직접 사용한다.
 * `@tulip/api-client.BaseClient`를 쓰지 않는 이유 —
 *   1) refresh 핸들러 의존 순환(`api-client → auth → api-client`) 방지
 *   2) 401 자동 refresh 인터셉터가 `/auth/refresh` 자체에 재귀 호출되는 걸 차단
 */
export class AuthClient {
  private readonly baseUrl: string;
  private readonly basePath: string;
  private readonly locale: string;
  private readonly storage: AuthStorage;
  private readonly fetchImpl: typeof fetch;

  constructor({ config, storage, fetchImpl }: AuthClientOptions) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.basePath = config.basePath ?? DEFAULT_BASE_PATH;
    this.locale = config.locale ?? 'ko-KR';
    this.storage = storage ?? createMemoryStorage();
    this.fetchImpl = fetchImpl ?? globalThis.fetch.bind(globalThis);
  }

  /** 인메모리 토큰 저장소(외부 공유용) */
  getStorage(): AuthStorage {
    return this.storage;
  }

  /** 현재 access token (만료 검사 없음, 호출 측에서 expiresAt 비교 권장) */
  getAccessToken(): string | null {
    return this.storage.getTokens()?.accessToken ?? null;
  }

  /** 현재 토큰 객체(전체) */
  getTokens(): AuthTokens | null {
    return this.storage.getTokens();
  }

  /**
   * 로그인 시작.
   *
   * @param returnUri 콜백 라우트 절대 URL (예: `${origin}/api/auth/callback`)
   * @param tenantHint 멀티테넌트 힌트(선택)
   * @returns `{ authorizationUrl, state }` — 브라우저가 authorizationUrl로 이동해야 한다.
   */
  async initiateLogin(returnUri: string, tenantHint?: string): Promise<LoginInitiateResponse> {
    const body: LoginInitiateRequest = { returnUri };
    if (tenantHint) body.tenantHint = tenantHint;
    return this.request<LoginInitiateResponse>('POST', '/login/initiate', body);
  }

  /**
   * 로그인 콜백 — code/state를 iam-service에 전달하여 token 교환.
   *
   * 성공 시:
   * - 응답 본문의 accessToken을 메모리 저장소에 저장
   * - HttpOnly Refresh 쿠키는 백엔드가 Set-Cookie 헤더로 자동 발급
   */
  async handleCallback(code: string, state: string): Promise<LoginCallbackResponse> {
    const body: LoginCallbackRequest = { code, state };
    const result = await this.request<LoginCallbackResponse>(
      'POST',
      '/login/callback',
      body,
    );
    this.storeAccessToken(result.accessToken, result.expiresIn);
    return result;
  }

  /**
   * Refresh — HttpOnly 쿠키로 access token 갱신.
   *
   * 401/403이면 null 반환(세션 만료로 간주).
   */
  async refresh(): Promise<AuthTokens | null> {
    try {
      const result = await this.request<RefreshResponse>('POST', '/refresh', undefined);
      const tokens = this.storeAccessToken(result.accessToken, result.expiresIn);
      return tokens;
    } catch (cause) {
      // 만료/무효 refresh는 명시적으로 null
      this.storage.setTokens(null);
      if (this.isUnauthorizedLike(cause)) return null;
      throw cause;
    }
  }

  /** 로그아웃 — 서버 쿠키 무효화 + 메모리 토큰 비우기 */
  async logout(): Promise<void> {
    try {
      await this.request<void>('POST', '/logout', undefined);
    } catch {
      // 로그아웃 호출 실패는 무시(쿠키가 이미 만료 등) — 클라이언트 상태는 항상 비운다
    } finally {
      this.storage.setTokens(null);
    }
  }

  /**
   * 현재 사용자 조회 — 세션 복원에 사용한다.
   * 인증되지 않은 상태(401)면 null을 반환한다.
   */
  async me(): Promise<AuthUser | null> {
    try {
      return await this.request<AuthUser>('GET', '/me', undefined);
    } catch (cause) {
      if (this.isUnauthorizedLike(cause)) return null;
      throw cause;
    }
  }

  // ──────────────────────────────────────────────────────────
  // 내부 유틸
  // ──────────────────────────────────────────────────────────

  private storeAccessToken(accessToken: string, expiresIn: number): AuthTokens {
    const tokens: AuthTokens = {
      accessToken,
      expiresAt: Date.now() + Math.max(0, expiresIn) * 1000,
    };
    this.storage.setTokens(tokens);
    return tokens;
  }

  private isUnauthorizedLike(err: unknown): boolean {
    if (err && typeof err === 'object' && 'status' in err) {
      const status = (err as { status?: number }).status;
      return status === 401 || status === 403;
    }
    return false;
  }

  private async request<T>(
    method: string,
    path: string,
    body: unknown,
  ): Promise<T> {
    const url = `${this.baseUrl}${this.basePath}${path}`;
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'Accept-Language': this.locale,
    };
    const init: RequestInit = {
      method,
      headers,
      // refresh token 쿠키 송수신 (Set-Cookie 포함)
      credentials: 'include',
    };
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json; charset=utf-8';
      init.body = JSON.stringify(body);
    }

    // 현재 access token이 있으면 Authorization 자동 첨부 (logout/me 등)
    const token = this.storage.getTokens()?.accessToken;
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await this.fetchImpl(url, init);

    if (res.status === 204) {
      return undefined as unknown as T;
    }

    let envelope: ApiEnvelope<T> | undefined;
    try {
      envelope = (await res.json()) as ApiEnvelope<T>;
    } catch {
      // 본문 없음/JSON 아님 — 상태 코드만으로 판단
      if (!res.ok) {
        throw Object.assign(new Error(`HTTP ${res.status}`), {
          status: res.status,
          code: `HTTP-${res.status}`,
        });
      }
      return undefined as unknown as T;
    }

    if (envelope && envelope.success === false) {
      throw Object.assign(new Error(envelope.message ?? envelope.code), {
        status: res.status,
        code: envelope.code,
        traceId: envelope.traceId,
        fieldErrors: envelope.fieldErrors,
      });
    }
    if (!res.ok) {
      throw Object.assign(new Error(`HTTP ${res.status}`), {
        status: res.status,
        code: envelope?.code ?? `HTTP-${res.status}`,
      });
    }

    return envelope?.data as T;
  }
}

/**
 * AuthClient 팩토리.
 */
export function createAuthClient(opts: AuthClientOptions): AuthClient {
  return new AuthClient(opts);
}
