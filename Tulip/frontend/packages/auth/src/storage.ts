/**
 * 인메모리 토큰 저장소 (Phase 1-B — BFF 패턴)
 *
 * - DEV-05 §2: access token은 메모리 보관(XSS 위험 최소화).
 * - refresh token은 iam-service가 HttpOnly Secure Cookie로 발급·관리한다.
 * - PKCE state/verifier도 iam-service 측에 있으므로 본 패키지는 다루지 않는다.
 *
 * 본 저장소는 단일 SPA 인스턴스 lifetime 동안 유효하며,
 * 페이지 새로고침 시 `/me` 또는 `/refresh` 호출로 재구성한다.
 */
import type { AuthTokens } from './types';

/** 토큰 변경 구독 콜백 */
export type TokenListener = (tokens: AuthTokens | null) => void;

export interface AuthStorage {
  getTokens(): AuthTokens | null;
  setTokens(tokens: AuthTokens | null): void;
  /** 토큰 변경 구독 (refresh 타이머 hook 등) */
  subscribe(listener: TokenListener): () => void;
  clear(): void;
}

class MemoryStorage implements AuthStorage {
  private tokens: AuthTokens | null = null;
  private listeners = new Set<TokenListener>();

  getTokens(): AuthTokens | null {
    return this.tokens;
  }

  setTokens(tokens: AuthTokens | null): void {
    this.tokens = tokens;
    this.listeners.forEach((l) => {
      try {
        l(tokens);
      } catch {
        /* listener 예외는 무시 (다른 listener 보호) */
      }
    });
  }

  subscribe(listener: TokenListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  clear(): void {
    this.setTokens(null);
  }
}

/**
 * 새 인메모리 저장소 생성.
 * Phase 1-B 기준 admin/opac 모두 동일 구현 사용.
 */
export function createMemoryStorage(): AuthStorage {
  return new MemoryStorage();
}

/**
 * @deprecated 브라우저 storage 기반 PKCE 저장소는 BFF 전환으로 제거됨.
 * 호환성을 위해 메모리 저장소로 alias.
 */
export const createBrowserStorage = createMemoryStorage;
