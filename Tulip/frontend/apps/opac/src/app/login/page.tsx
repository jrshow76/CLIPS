import { Suspense } from 'react';

import { LoginForm } from './_components/LoginForm';

export const metadata = { title: '로그인 — Tulip+ OPAC' };

export default function LoginPage() {
  return (
    <div className="container-opac mx-auto flex max-w-[480px] flex-col items-center px-4 py-10 sm:px-6">
      <header className="mb-6 text-center">
        <div aria-hidden="true" className="text-4xl">
          🌷
        </div>
        <h1 className="mt-2 text-h1 text-neutral-900">로그인</h1>
        <p className="mt-1 text-[14px] text-neutral-600">
          회원 번호 또는 통합ID로 로그인하세요.
        </p>
      </header>
      {/* useSearchParams를 사용하므로 Suspense boundary 필요 */}
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
