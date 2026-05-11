/**
 * @tulip/auth — iam-service `/api/v1/auth/*` 위임 인증 클라이언트
 *
 * Phase 1-B: BFF 패턴 — PKCE state/verifier는 iam-service가 보관하고
 * SPA는 단순히 `/login/initiate`, `/login/callback`, `/refresh`, `/me`, `/logout`을
 * 호출한다. accessToken은 메모리, refreshToken은 HttpOnly Secure 쿠키.
 *
 * 보안 표준은 DEV-05 §2 (`05_security_and_auth.md`)를 따른다.
 *
 * NOTE: 클라이언트 측 PKCE 유틸(`pkce.ts`)은 deprecated 처리되어
 * 본 모듈에서 re-export 하지 않는다. 필요한 경우 직접 import.
 */
export * from './types';
export * from './storage';
export * from './client';
export * from './context';
export * from './useAuth';
