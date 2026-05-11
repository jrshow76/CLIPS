/**
 * @tulip/auth — OAuth2 Authorization Code + PKCE 클라이언트
 *
 * - DEV-05 §2 보안 정책에 따라 access token은 메모리, refresh token은 HttpOnly Cookie 권장.
 * - Phase 1-A 본 단계에서는 인터페이스와 mock 구현을 제공.
 * - 실제 IAM(Keycloak) 연동은 Phase 1-B에서 토큰 엔드포인트 호출로 교체.
 */
export * from './types';
export * from './pkce';
export * from './storage';
export * from './client';
export * from './context';
export * from './useAuth';
