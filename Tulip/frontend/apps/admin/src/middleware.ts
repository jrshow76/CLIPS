/**
 * 보호 라우트 미들웨어 (Edge 런타임).
 *
 * - `(shell)/*`로 매핑되는 모든 페이지에 인증을 강제한다.
 * - 인증 여부 판단은 **refresh 쿠키 존재만** 확인한다 (성능·안정성 이유).
 *   - 실제 토큰 유효성은 페이지 mount 시 `useAuth.bootstrap`에서 `/me`로 검증.
 *   - 쿠키 자체가 없으면 어차피 백엔드 호출이 실패하므로 미리 차단.
 * - 보호 라우트에 미인증으로 진입 시 `/login?next=<원경로>`로 302.
 *
 * NOTE: HttpOnly 쿠키는 백엔드 도메인에서 발급될 수 있다.
 *   - 같은 도메인(예: Gateway 경유 동일 host)이면 Next 서버에서 쿠키를 직접 읽을 수 있음.
 *   - 다른 도메인이면 미들웨어에서 쿠키 검사를 생략하고 client-side에서만 검증.
 *     `NEXT_PUBLIC_AUTH_COOKIE_NAME`이 설정된 경우에만 검사하도록 옵션화.
 */
import { NextResponse, type NextRequest } from 'next/server';

/** iam-service가 발급하는 refresh 쿠키 이름 (백엔드와 합의된 키) */
const AUTH_COOKIE_NAME =
  process.env.NEXT_PUBLIC_AUTH_COOKIE_NAME ?? 'tulip_refresh';

/** 익명으로 접근 가능한 경로 */
const PUBLIC_PATHS = [
  '/login',
  '/auth/callback',
  '/api/auth/callback',
  '/help',
];

function isPublic(pathname: string): boolean {
  if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return true;
  }
  // Next 내부 리소스
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/favicon') ||
    pathname.startsWith('/assets')
  ) {
    return true;
  }
  return false;
}

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;

  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  const hasRefreshCookie = req.cookies.has(AUTH_COOKIE_NAME);
  if (hasRefreshCookie) {
    return NextResponse.next();
  }

  // 미인증 → /login으로 리다이렉트, 원래 경로 유지
  const loginUrl = req.nextUrl.clone();
  loginUrl.pathname = '/login';
  loginUrl.search = `?next=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(loginUrl);
}

export const config = {
  /**
   * 보호 라우트 매처.
   * - `_next/*`, `favicon`, 정적 자산, `/login`, `/auth/callback`, `/api/auth/callback`는 제외.
   * - 나머지 모든 경로(대시보드·도메인 페이지 등)는 인증 검사 대상.
   */
  matcher: ['/((?!_next/|favicon|assets/|login|auth/callback|api/auth/callback|help).*)'],
};
