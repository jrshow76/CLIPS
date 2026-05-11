/**
 * OAuth2 콜백 Route Handler (Next.js App Router).
 *
 * Keycloak이 returnUri로 지정된 `${origin}/api/auth/callback`에 redirect 한다.
 * 본 핸들러는 단순히 SPA의 client-side 콜백 페이지(`/auth/callback`)로
 * code/state 쿼리스트링을 전파한다.
 *
 * 보안 검토 결과 — **client-side 콜백** 채택 이유:
 * - HttpOnly Refresh 쿠키는 iam-service(API 도메인)가 직접 Set-Cookie 하므로,
 *   Next 서버에서 토큰 교환을 중계할 경우 cookie 도메인 정합성 문제가 생길 수 있다.
 * - 본 핸들러에서 백엔드 호출 없이 SPA로 전달 → SPA가 `credentials: 'include'`로
 *   `/login/callback` 호출 → 백엔드가 SPA 도메인이 아닌 API 도메인으로 쿠키 발급.
 * - 토큰은 응답 본문(accessToken)으로만 받아 메모리 보관.
 *
 * code/state는 일회용·짧은 수명이고 iam-service에서만 검증되므로
 * URL 노출로 인한 추가 위험은 최소화된다.
 */
import { NextResponse, type NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

export function GET(req: NextRequest) {
  const { searchParams, origin } = new URL(req.url);
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const next = searchParams.get('next') ?? '/dashboard';
  const errorParam = searchParams.get('error');

  // 에러 발생 시 로그인 페이지로 메시지 전달
  if (errorParam) {
    const url = new URL('/login', origin);
    url.searchParams.set('error', errorParam);
    return NextResponse.redirect(url);
  }

  if (!code || !state) {
    const url = new URL('/login', origin);
    url.searchParams.set('error', 'invalid_callback');
    return NextResponse.redirect(url);
  }

  // SPA 콜백 페이지로 전달 — 클라이언트가 백엔드 /login/callback 호출.
  const target = new URL('/auth/callback', origin);
  target.searchParams.set('code', code);
  target.searchParams.set('state', state);
  target.searchParams.set('next', next);
  return NextResponse.redirect(target);
}
