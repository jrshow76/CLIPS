'use client';

import { Button, FormField, Input } from '@tulip/ui';
import { useState } from 'react';

/**
 * 로그인 폼 (Phase 1-A 스켈레톤).
 * 실제 인증 흐름(OAuth2 PKCE)은 Phase 1-B에서 @tulip/auth 와 통합.
 */
export function LoginForm() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setError('Phase 1-A 단계에서는 로그인 동작이 아직 연결되지 않았습니다.');
    }, 600);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-neutral-200 bg-surface-card p-6 shadow-sm"
    >
      <div className="flex flex-col gap-4">
        <FormField label="아이디" required>
          {({ id, ...a11y }) => (
            <Input id={id} type="text" autoComplete="username" placeholder="librarian01" {...a11y} />
          )}
        </FormField>
        <FormField label="비밀번호" required>
          {({ id, ...a11y }) => (
            <Input id={id} type="password" autoComplete="current-password" {...a11y} />
          )}
        </FormField>
        {error && (
          <p role="alert" className="text-[13px] text-danger">
            {error}
          </p>
        )}
        <Button type="submit" loading={loading} fullWidth>
          로그인
        </Button>
        <p className="text-center text-[12px] text-neutral-500">
          비밀번호를 잊으셨나요?{' '}
          <a href="#" className="text-primary-600 underline-offset-2 hover:underline">
            도움말
          </a>
        </p>
      </div>
    </form>
  );
}
