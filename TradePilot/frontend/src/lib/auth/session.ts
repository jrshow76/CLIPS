/**
 * 인증 세션 토큰 저장소.
 *
 * 보안 노트(인계):
 *   - 운영 환경에서는 access/refresh 토큰을 **httpOnly + Secure + SameSite=Lax** 쿠키로 발급받는
 *     BFF 모델이 우선이다. 본 모듈은 개발 편의를 위한 localStorage fallback이며,
 *     XSS 노출 가능성이 있다. 운영 전환 시 백엔드와 협의하여 쿠키 모드로 교체할 것.
 *   - access 토큰 만료(30분) 1분 이전에 refresh 시도하도록 client.ts 인터셉터가 처리.
 */

const ACCESS_KEY = 'tp.access_token';
const REFRESH_KEY = 'tp.refresh_token';
const EXPIRES_KEY = 'tp.access_expires_at';

const isBrowser = typeof window !== 'undefined';

export interface SessionTokens {
  access_token: string;
  refresh_token?: string;
  expires_at: number; // epoch ms
}

export const session = {
  get(): SessionTokens | null {
    if (!isBrowser) return null;
    const access = localStorage.getItem(ACCESS_KEY);
    const refresh = localStorage.getItem(REFRESH_KEY) ?? undefined;
    const expiresAt = Number(localStorage.getItem(EXPIRES_KEY) ?? 0);
    if (!access) return null;
    return { access_token: access, refresh_token: refresh, expires_at: expiresAt };
  },
  set(tokens: { access_token: string; refresh_token?: string; expires_in: number }): void {
    if (!isBrowser) return;
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    if (tokens.refresh_token) localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    const expiresAt = Date.now() + tokens.expires_in * 1000;
    localStorage.setItem(EXPIRES_KEY, String(expiresAt));
  },
  clear(): void {
    if (!isBrowser) return;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(EXPIRES_KEY);
  },
  isExpired(): boolean {
    if (!isBrowser) return true;
    const expiresAt = Number(localStorage.getItem(EXPIRES_KEY) ?? 0);
    return Date.now() >= expiresAt - 60_000; // 만료 1분 전 갱신 트리거
  },
};
