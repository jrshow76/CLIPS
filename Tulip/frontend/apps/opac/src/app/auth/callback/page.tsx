import { Suspense } from 'react';

import { CallbackHandler } from './_components/CallbackHandler';

export const metadata = { title: '로그인 처리 중 — Tulip+ OPAC' };

export default function AuthCallbackPage() {
  return (
    <div className="container-opac mx-auto flex max-w-[480px] flex-col items-center px-4 py-10 sm:px-6">
      <Suspense
        fallback={
          <p className="text-[14px] text-neutral-600">로그인 처리 중…</p>
        }
      >
        <CallbackHandler />
      </Suspense>
    </div>
  );
}
