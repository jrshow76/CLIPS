/**
 * 인증 타입 (Phase 1-B — BFF 패턴)
 *
 * iam-service `/api/v1/auth/*` 응답 구조에 맞춰 정의한다.
 * - PKCE 상태(verifier·state)는 iam-service가 보관하므로 클라이언트는 운반하지 않는다.
 * - accessToken은 메모리, refreshToken은 HttpOnly Secure Cookie로 자동 운영.
 */

export type MemberType = 'STAFF' | 'PATRON' | 'DEVICE' | 'PLATFORM_ADMIN';

/**
 * `GET /api/v1/auth/me` 응답 데이터.
 *
 * iam-service 명세에 맞춰 표준화한 필드:
 * - userId(sub), name, email
 * - tenantId, branchIds, roles, scopes
 */
export interface AuthUser {
  /** sub claim — 사용자 ID */
  userId: string;
  /** 표시 이름 */
  name: string;
  /** 이메일 */
  email?: string;
  /** 회원 유형 (STAFF/PATRON/DEVICE/PLATFORM_ADMIN) */
  memberType?: MemberType;
  /** 테넌트 ID */
  tenantId: string;
  /** 권한 있는 관 목록 */
  branchIds: string[];
  /** 현재 활성 관(서버가 지정한 기본 관) */
  primaryBranchId?: string;
  /** 역할 (RBAC) */
  roles: string[];
  /** 스코프 (`{domain}:{action}`) */
  scopes: string[];
  /** 인증 방식 (amr) — pwd, mfa, sso 등 */
  amr?: string[];
}

/**
 * 로그인 시작 요청.
 * - returnUri: 로그인 완료 후 돌아갈 SPA 경로(절대 URL).
 *   iam-service가 Keycloak `redirect_uri`로 사용한다.
 * - tenantHint: 멀티테넌트에서 사전 힌트가 있을 때 (없으면 공통 로그인).
 */
export interface LoginInitiateRequest {
  returnUri: string;
  tenantHint?: string;
}

/**
 * 로그인 시작 응답 — iam-service가 PKCE state/verifier를 보관하고
 * Keycloak authorize URL을 만들어 돌려준다.
 */
export interface LoginInitiateResponse {
  /** 브라우저가 redirect할 Keycloak `/authorize` URL */
  authorizationUrl: string;
  /** CSRF 방어용 opaque state (서버가 발급, 클라이언트는 단순 전달) */
  state: string;
}

/**
 * 로그인 콜백 요청.
 * - Keycloak이 `returnUri`에 code/state를 붙여 redirect → SPA가 그대로 백엔드로 위임.
 */
export interface LoginCallbackRequest {
  code: string;
  state: string;
}

/**
 * 로그인 콜백 응답 — iam-service가 code+state를 token으로 교환한 결과.
 * refreshToken은 응답 body에 포함되지 않고 HttpOnly 쿠키로 발급된다.
 */
export interface LoginCallbackResponse {
  /** access token (메모리에만 보관) */
  accessToken: string;
  /** 만료까지 남은 초 */
  expiresIn: number;
  /** 사용자 정보 */
  user: AuthUser;
}

/**
 * Refresh 응답 — HttpOnly 쿠키로 전송된 refresh token으로 access만 갱신.
 */
export interface RefreshResponse {
  accessToken: string;
  expiresIn: number;
}

/** 인메모리 토큰 상태 */
export interface AuthTokens {
  accessToken: string;
  /** access token 만료시각 (epoch ms) */
  expiresAt: number;
}

/**
 * @tulip/auth 클라이언트 생성 시 전달하는 설정.
 */
export interface AuthClientConfig {
  /** API base URL — Gateway 주소 (예: http://localhost:9100) */
  baseUrl: string;
  /** 인증 엔드포인트 prefix (기본: `/api/v1/auth`) */
  basePath?: string;
  /** Accept-Language */
  locale?: string;
}

/** 인증 상태 분류 */
export type AuthStatus = 'idle' | 'loading' | 'authenticated' | 'unauthenticated' | 'error';

/**
 * @deprecated Phase 1-A 호환용. BFF 패턴(Phase 1-B)으로 전환됐으므로
 * 클라이언트 측에서 PKCE challenge를 직접 생성하지 않는다.
 */
export interface PkceChallenge {
  codeVerifier: string;
  codeChallenge: string;
  state: string;
  nonce: string;
}
