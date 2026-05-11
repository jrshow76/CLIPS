/**
 * OPAC 미들웨어 — 보호 라우트(`/me/*`, `/loans/*`, `/holds/*`)만 인증 강제.
 *
 * 검색·자료 상세 등은 비로그인 허용. 익명 라우트는 통과.
 */
import { NextResponse, type NextRequest } from 'next/server';

const AUTH_COOKIE_NAME =
  process.env.NEXT_PUBLIC_AUTH_COOKIE_NAME ?? 'tulip_refresh';

/** 인증 강제 prefix */
const PROTECTED_PREFIXES = ['/me', '/loans', '/holds'];

function isProtected(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );
}

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;

  if (!isProtected(pathname)) {
    return NextResponse.next();
  }

  if (req.cookies.has(AUTH_COOKIE_NAME)) {
    return NextResponse.next();
  }

  const loginUrl = req.nextUrl.clone();
  loginUrl.pathname = '/login';
  loginUrl.search = `?next=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(loginUrl);
}

export const config = {
  // 정적 자산·Next 내부는 제외
  matcher: ['/((?!_next/|favicon|assets/|api/auth/callback).*)'],
};
