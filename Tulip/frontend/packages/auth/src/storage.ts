/**
 * 토큰 저장소 추상화
 *
 * - DEV-05: refresh token 은 HttpOnly Secure Cookie 권장 → 서버측 처리.
 * - access token 은 in-memory 권장 (XSS 위험 최소화).
 * - PKCE verifier · state 는 짧은 TTL의 sessionStorage 사용.
 */
import type { AuthTokens } from './types';

export interface AuthStorage {
  getTokens: () => AuthTokens | null;
  setTokens: (tokens: AuthTokens | null) => void;
  getPkceVerifier: (state: string) => string | null;
  setPkceVerifier: (state: string, verifier: string) => void;
  clearPkce: () => void;
}

class MemoryStorage implements AuthStorage {
  private tokens: AuthTokens | null = null;
  private verifiers = new Map<string, string>();

  getTokens(): AuthTokens | null {
    return this.tokens;
  }

  setTokens(tokens: AuthTokens | null): void {
    this.tokens = tokens;
  }

  getPkceVerifier(state: string): string | null {
    return this.verifiers.get(state) ?? null;
  }

  setPkceVerifier(state: string, verifier: string): void {
    this.verifiers.set(state, verifier);
  }

  clearPkce(): void {
    this.verifiers.clear();
  }
}

const PKCE_KEY_PREFIX = 'tulip.auth.pkce.';

class SessionStorageBackedStorage implements AuthStorage {
  private tokens: AuthTokens | null = null;

  getTokens(): AuthTokens | null {
    return this.tokens;
  }

  setTokens(tokens: AuthTokens | null): void {
    this.tokens = tokens;
  }

  getPkceVerifier(state: string): string | null {
    if (typeof window === 'undefined') return null;
    return window.sessionStorage.getItem(`${PKCE_KEY_PREFIX}${state}`);
  }

  setPkceVerifier(state: string, verifier: string): void {
    if (typeof window === 'undefined') return;
    window.sessionStorage.setItem(`${PKCE_KEY_PREFIX}${state}`, verifier);
  }

  clearPkce(): void {
    if (typeof window === 'undefined') return;
    const toRemove: string[] = [];
    for (let i = 0; i < window.sessionStorage.length; i += 1) {
      const key = window.sessionStorage.key(i);
      if (key?.startsWith(PKCE_KEY_PREFIX)) toRemove.push(key);
    }
    toRemove.forEach((k) => window.sessionStorage.removeItem(k));
  }
}

export function createMemoryStorage(): AuthStorage {
  return new MemoryStorage();
}

export function createBrowserStorage(): AuthStorage {
  return new SessionStorageBackedStorage();
}
