import { Suspense } from 'react';

import { CallbackHandler } from './_components/CallbackHandler';

export const metadata = { title: '로그인 처리 중 — Tulip+ Admin' };

/**
 * Client-side 콜백 페이지.
 * useSearchParams가 CSR에서 동작하므로 Suspense boundary로 감싼다.
 */
export default function AuthCallbackPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-surface-app px-4">
      <Suspense
        fallback={
          <p className="text-[14px] text-neutral-600">로그인 처리 중…</p>
        }
      >
        <CallbackHandler />
      </Suspense>
    </main>
  );
}
