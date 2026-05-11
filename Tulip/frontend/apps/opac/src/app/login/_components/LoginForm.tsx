'use client';

import { useAuth } from '@tulip/auth';
import { Button } from '@tulip/ui';
import { useSearchParams } from 'next/navigation';
import { useState } from 'react';

/**
 * OPAC 이용자 로그인 폼 (Phase 1-B / BFF 패턴).
 *
 * Keycloak `opac-web` 클라이언트로 위임한다. 본 페이지에서는 자격증명을 받지 않는다.
 * 회원가입·간편 로그인(카카오/네이버/mIDR)도 동일한 입구를 통해 처리된다.
 */
export function LoginForm() {
  const { login } = useAuth();
  const params = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function resolveReturnPath(): string {
    const next = params?.get('next');
    if (!next) return '/me';
    if (!/^\/[^/]/.test(next) && next !== '/') return '/me';
    return next;
  }

  async function handleLogin() {
    setError(null);
    setLoading(true);
    try {
      const origin = window.location.origin;
      const returnUri = `${origin}/api/auth/callback?next=${encodeURIComponent(resolveReturnPath())}`;
      await login(returnUri);
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
    <div className="w-full rounded-2xl border border-neutral-200 bg-surface-card p-6 shadow-sm">
      <div className="flex flex-col gap-4">
        <p className="text-[14px] text-neutral-600">
          회원 번호 또는 통합ID로 로그인합니다. 도서관 통합 SSO 페이지로 이동합니다.
        </p>
        {error && (
          <p role="alert" className="text-[13px] text-danger">
            {error}
          </p>
        )}
        <Button type="button" loading={loading} fullWidth onClick={handleLogin}>
          로그인
        </Button>
        <div className="flex justify-between text-[12px] text-neutral-500">
          <a href="/help/login" className="text-primary-600 underline-offset-2 hover:underline">
            로그인 도움말
          </a>
          <a href="/signup" className="text-primary-600 underline-offset-2 hover:underline">
            회원가입
          </a>
        </div>
      </div>
    </div>
  );
}
