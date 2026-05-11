/**
 * OPAC OAuth2 콜백 Route Handler.
 *
 * admin과 동일하게 client-side 콜백 페이지(`/auth/callback`)로 전파한다.
 */
import { NextResponse, type NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

export function GET(req: NextRequest) {
  const { searchParams, origin } = new URL(req.url);
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const next = searchParams.get('next') ?? '/me';
  const errorParam = searchParams.get('error');

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

  const target = new URL('/auth/callback', origin);
  target.searchParams.set('code', code);
  target.searchParams.set('state', state);
  target.searchParams.set('next', next);
  return NextResponse.redirect(target);
}
