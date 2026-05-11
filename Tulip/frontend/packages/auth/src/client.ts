/**
 * AuthClient — OAuth2 Authorization Code + PKCE 클라이언트
 *
 * Phase 1-A: 인터페이스 + mock 구현.
 * Phase 1-B: Keycloak `/protocol/openid-connect/token` 엔드포인트 호출로 교체.
 */
import { generatePkceChallenge } from './pkce';
import { createBrowserStorage, type AuthStorage } from './storage';
import type { AuthTokens, AuthUser, OAuth2Config } from './types';

export interface AuthClientOptions {
  config: OAuth2Config;
  storage?: AuthStorage;
}

export class AuthClient {
  private readonly config: OAuth2Config;
  private readonly storage: AuthStorage;
  /** TODO(Phase 1-B): Keycloak 디스커버리 (.well-known/openid-configuration) 캐싱 */
  private discovery?: { authorization_endpoint: string; token_endpoint: string; end_session_endpoint?: string };

  constructor({ config, storage }: AuthClientOptions) {
    this.config = config;
    this.storage = storage ?? createBrowserStorage();
  }

  /**
   * 로그인 시작 — PKCE 챌린지 생성 후 authorize URL 로 리다이렉트.
   */
  async beginLogin(): Promise<string> {
    const challenge = await generatePkceChallenge();
    this.storage.setPkceVerifier(challenge.state, challenge.codeVerifier);

    const url = new URL(`${this.config.issuer}/protocol/openid-connect/auth`);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('client_id', this.config.clientId);
    url.searchParams.set('redirect_uri', this.config.redirectUri);
    url.searchParams.set('scope', this.config.scopes.join(' '));
    url.searchParams.set('state', challenge.state);
    url.searchParams.set('nonce', challenge.nonce);
    url.searchParams.set('code_challenge', challenge.codeChallenge);
    url.searchParams.set('code_challenge_method', 'S256');
    return url.toString();
  }

  /**
   * 콜백 처리 — code + state 검증 후 토큰 교환.
   * (Phase 1-B에서 실제 token endpoint 호출로 교체)
   */
  async completeLogin(_params: { code: string; state: string }): Promise<AuthTokens> {
    const verifier = this.storage.getPkceVerifier(_params.state);
    if (!verifier) {
      throw new Error('PKCE verifier 누락 또는 state 검증 실패');
    }
    this.storage.clearPkce();

    // TODO(Phase 1-B): fetch(token_endpoint, grant_type=authorization_code + code_verifier)
    const mockTokens: AuthTokens = {
      accessToken: 'mock.access.token',
      expiresAt: Date.now() + 5 * 60 * 1000,
      refreshToken: null, // HttpOnly Cookie 가정
      tokenType: 'Bearer',
    };
    this.storage.setTokens(mockTokens);
    return mockTokens;
  }

  /**
   * Refresh — refresh_token으로 새 access token 발급.
   * (HttpOnly Cookie 흐름: 서버에 fetch 요청)
   */
  async refresh(): Promise<AuthTokens | null> {
    // TODO(Phase 1-B): fetch('/auth/refresh', { credentials: 'include' })
    const tokens = this.storage.getTokens();
    if (!tokens) return null;
    const refreshed: AuthTokens = {
      ...tokens,
      accessToken: `${tokens.accessToken}.refreshed`,
      expiresAt: Date.now() + 5 * 60 * 1000,
    };
    this.storage.setTokens(refreshed);
    return refreshed;
  }

  /** 로그아웃 — 토큰 폐기 후 IdP 로그아웃 URL 반환 */
  async logout(): Promise<string> {
    this.storage.setTokens(null);
    const url = new URL(`${this.config.issuer}/protocol/openid-connect/logout`);
    url.searchParams.set('client_id', this.config.clientId);
    if (this.config.postLogoutRedirectUri) {
      url.searchParams.set('post_logout_redirect_uri', this.config.postLogoutRedirectUri);
    }
    return url.toString();
  }

  /** 현재 access token (만료 처리 미포함, 클라이언트는 추가 검사) */
  getAccessToken(): string | null {
    return this.storage.getTokens()?.accessToken ?? null;
  }

  /** 현재 토큰 객체 */
  getTokens(): AuthTokens | null {
    return this.storage.getTokens();
  }

  /**
   * 사용자 정보 조회 (mock).
   * Phase 1-B: ID Token decode 또는 `/userinfo` 엔드포인트 호출.
   */
  async getUser(): Promise<AuthUser | null> {
    const tokens = this.storage.getTokens();
    if (!tokens) return null;
    return {
      id: 'mock_user_01',
      name: 'Mock 사용자',
      email: 'mock@tulip.example.com',
      memberType: 'STAFF',
      tenantId: 'tnt_demo',
      libraryIds: ['lib_main'],
      primaryBranchId: 'lib_main',
      roles: ['LIBRARIAN_HEAD'],
      scopes: ['cat:read', 'cat:write', 'cir:read', 'cir:write', 'opac:read'],
      amr: ['pwd'],
    };
  }
}

export function createAuthClient(opts: AuthClientOptions): AuthClient {
  return new AuthClient(opts);
}
