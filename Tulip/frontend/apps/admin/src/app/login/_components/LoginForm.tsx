'use client';

import { useAuth } from '@tulip/auth';
import { Button } from '@tulip/ui';
import { useSearchParams } from 'next/navigation';
import { useState } from 'react';

/**
 * 관리자 로그인 폼 (Phase 1-B / BFF 패턴).
 *
 * - 자격증명은 본 페이지에서 받지 않는다. (Keycloak 로그인 페이지로 redirect)
 * - "Keycloak으로 로그인" 클릭 → iam-service `/login/initiate` 호출
 *   → 받은 authorizationUrl로 `window.location.assign`.
 * - 콜백은 `/api/auth/callback`(Route Handler)에서 처리되어 SPA 콜백 페이지로 전달된다.
 */
export function LoginForm() {
  const { login } = useAuth();
  const params = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** 로그인 완료 후 돌아갈 SPA 경로 (?next=...). 안전한 동일 출처만 허용. */
  function resolveReturnPath(): string {
    const next = params?.get('next');
    if (!next) return '/dashboard';
    // 외부 redirect 방지 — '/'로 시작하는 동일 출처 경로만 허용
    if (!/^\/[^/]/.test(next) && next !== '/') return '/dashboard';
    return next;
  }

  async function handleLogin() {
    setError(null);
    setLoading(true);
    try {
      const origin = window.location.origin;
      // SPA 콜백 URL — Next.js Route Handler가 받음.
      const returnUri = `${origin}/api/auth/callback?next=${encodeURIComponent(resolveReturnPath())}`;
      await login(returnUri);
      // login()은 IdP로 redirect — 정상 흐름에서는 아래 코드에 도달하지 않음.
    } catch (cause) {
      setLoading(false);
      setError(
        cause instanceof Error
          ? `로그인 시작 실패: ${cause.message}`
          : '로그인 시작에 실패했습니다. 잠시 후 다시 시도하세요.',
      );
    }
  }

  return (
    <div className="rounded-xl border border-neutral-200 bg-surface-card p-6 shadow-sm">
      <div className="flex flex-col gap-4">
        <p className="text-[13px] text-neutral-600">
          Keycloak SSO로 로그인합니다. 학교 SSO·기관 계정 연동도 동일한 입구를 사용합니다.
        </p>
        {error && (
          <p role="alert" className="text-[13px] text-danger">
            {error}
          </p>
        )}
        <Button type="button" loading={loading} fullWidth onClick={handleLogin}>
          Keycloak으로 로그인
        </Button>
        <p className="text-center text-[12px] text-neutral-500">
          문제가 있으신가요?{' '}
          <a href="/help/login" className="text-primary-600 underline-offset-2 hover:underline">
            로그인 도움말
          </a>
        </p>
      </div>
    </div>
  );
}
