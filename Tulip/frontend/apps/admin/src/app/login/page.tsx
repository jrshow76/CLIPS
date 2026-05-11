import type { Metadata } from 'next';

import { LoginForm } from './_components/LoginForm';

export const metadata: Metadata = { title: '로그인 — Tulip+ Admin' };

export default function LoginPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-surface-app px-4">
      <div className="w-full max-w-sm">
        <header className="mb-6 text-center">
          <div aria-hidden="true" className="text-4xl">
            🌷
          </div>
          <h1 className="mt-2 text-h2 text-neutral-900">Tulip+ 관리자</h1>
          <p className="mt-1 text-[13px] text-neutral-600">
            사서·관리자 계정으로 로그인하세요.
          </p>
        </header>
        <LoginForm />
      </div>
    </main>
  );
}
