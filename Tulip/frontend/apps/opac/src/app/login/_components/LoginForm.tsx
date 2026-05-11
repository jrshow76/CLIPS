'use client';

import { Button, FormField, Input } from '@tulip/ui';

/**
 * OPAC 로그인 폼 (Phase 1-A 스켈레톤).
 * 실제 인증 흐름(OAuth2 PKCE)은 Phase 1-B에서 @tulip/auth 와 통합.
 */
export function LoginForm() {
  return (
    <form className="w-full rounded-2xl border border-neutral-200 bg-surface-card p-6 shadow-sm">
      <div className="flex flex-col gap-4">
        <FormField label="아이디" required>
          {({ id, ...a11y }) => (
            <Input id={id} type="text" autoComplete="username" {...a11y} />
          )}
        </FormField>
        <FormField label="비밀번호" required>
          {({ id, ...a11y }) => (
            <Input id={id} type="password" autoComplete="current-password" {...a11y} />
          )}
        </FormField>
        <Button type="submit" fullWidth>
          로그인
        </Button>
      </div>
    </form>
  );
}
