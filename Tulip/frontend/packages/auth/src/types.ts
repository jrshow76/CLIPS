/**
 * 인증 타입
 */

export type MemberType = 'STAFF' | 'PATRON' | 'DEVICE' | 'PLATFORM_ADMIN';

export interface AuthUser {
  /** sub claim — 사용자 ID */
  id: string;
  /** 표시 이름 */
  name: string;
  /** 이메일 */
  email?: string;
  /** 회원 유형 */
  memberType: MemberType;
  /** 테넌트 ID */
  tenantId: string;
  /** 권한 있는 관 목록 */
  libraryIds: string[];
  /** 현재 활성 관 */
  primaryBranchId?: string;
  /** 역할 (RBAC) */
  roles: string[];
  /** 스코프 (`{domain}:{action}`) */
  scopes: string[];
  /** 인증 방식 (amr) — pwd, mfa, sso 등 */
  amr?: string[];
}

export interface AuthTokens {
  accessToken: string;
  /** access token 만료시각 (epoch ms) */
  expiresAt: number;
  /** refresh token (HttpOnly Cookie 사용 시 클라이언트는 null) */
  refreshToken?: string | null;
  tokenType: 'Bearer';
}

export interface OAuth2Config {
  /** IAM issuer URL (예: https://iam.tulip.example.com/realms/tulip) */
  issuer: string;
  /** 클라이언트 ID */
  clientId: string;
  /** 리디렉트 URI */
  redirectUri: string;
  /** 요청 스코프 */
  scopes: string[];
  /** 로그아웃 후 이동 URL */
  postLogoutRedirectUri?: string;
}

export type AuthStatus =
  | { status: 'idle' }
  | { status: 'authenticating' }
  | { status: 'authenticated'; user: AuthUser; tokens: AuthTokens }
  | { status: 'unauthenticated' }
  | { status: 'error'; error: Error };

export interface PkceChallenge {
  codeVerifier: string;
  codeChallenge: string;
  state: string;
  nonce: string;
}
