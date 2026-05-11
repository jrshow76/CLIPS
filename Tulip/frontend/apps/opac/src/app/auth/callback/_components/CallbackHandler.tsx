'use client';

import { useAuth } from '@tulip/auth';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

/**
 * OPAC OAuth2 콜백 처리 — code/state로 iam-service `/login/callback` 호출.
 */
export function CallbackHandler() {
  const router = useRouter();
  const params = useSearchParams();
  const { handleCallback } = useAuth();
  const startedRef = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const code = params?.get('code');
    const state = params?.get('state');
    const next = params?.get('next') ?? '/me';

    if (!code || !state) {
      setError('잘못된 콜백 요청입니다.');
      return;
    }

    handleCallback({ code, state })
      .then(() => router.replace(safePath(next)))
      .catch((cause: unknown) => {
        const message =
          cause instanceof Error ? cause.message : '로그인 처리에 실패했습니다.';
        setError(message);
      });
  }, [params, handleCallback, router]);

  if (error) {
    return (
      <div
        role="alert"
        className="max-w-sm rounded-xl border border-danger bg-surface-card p-6 text-center"
      >
        <p className="text-[14px] text-danger">{error}</p>
        <a
          href="/login"
          className="mt-3 inline-block text-[13px] text-primary-600 underline-offset-2 hover:underline"
        >
          로그인 페이지로 돌아가기
        </a>
      </div>
    );
  }

  return <p className="text-[14px] text-neutral-600">로그인 처리 중…</p>;
}

function safePath(p: string): string {
  if (!p.startsWith('/')) return '/me';
  if (p.startsWith('//')) return '/me';
  return p;
}
