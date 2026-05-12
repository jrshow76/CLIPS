'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { ErrorCard } from '@/components/ui/error-card';
import { Field, Input } from '@/components/ui/input';
import { useSignup } from '@/lib/api/queries/auth';
import { ROUTES } from '@/lib/constants';

export default function SignupPage() {
  const router = useRouter();
  const signup = useSignup();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await signup.mutateAsync({ email, password, nickname });
      router.push(ROUTES.LOGIN);
    } catch (err) {
      const e = err as { userMessage?: string; message: string };
      setError(e.userMessage ?? e.message);
    }
  }

  return (
    <main className="center" style={{ minHeight: '100vh', padding: 'var(--space-6)' }}>
      <form onSubmit={onSubmit} className="card" style={{ width: '100%', maxWidth: 420 }}>
        <header className="card__header">
          <h1 className="card__title">회원가입</h1>
        </header>
        <div className="card__body stack gap-4">
          <Field label="이메일" htmlFor="email" required>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@trade.com"
              required
            />
          </Field>
          <Field label="닉네임" htmlFor="nickname" required>
            <Input
              id="nickname"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="2~16자"
              required
            />
          </Field>
          <Field label="비밀번호" htmlFor="password" required hint="8~32자, 영문+숫자+특수문자 포함">
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Field>
          {error && <ErrorCard title="가입 실패" message={error} />}
        </div>
        <footer className="card__footer row items-center justify-between">
          <Link href={ROUTES.LOGIN} className="text-sm" style={{ color: 'var(--color-brand-300)' }}>
            이미 계정이 있나요?
          </Link>
          <Button type="submit" variant="primary" loading={signup.isPending}>
            가입
          </Button>
        </footer>
      </form>
    </main>
  );
}
