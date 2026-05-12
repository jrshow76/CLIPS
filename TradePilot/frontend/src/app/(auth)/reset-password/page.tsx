'use client';

import { CheckCircle2, KeyRound, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { Button } from '@/components/ui/button';
import { ErrorCard } from '@/components/ui/error-card';
import { Field, Input } from '@/components/ui/input';
import { ROUTES } from '@/lib/constants';
import { applyFieldErrors, toUserMessage } from '@/lib/forms/extract-field-errors';
import { evaluatePassword, resetPasswordSchema, type ResetPasswordForm } from '@/lib/forms/zod-schemas';
import { zodResolver } from '@/lib/forms/zod-resolver';
import { cn } from '@/lib/utils/cn';
import { toast } from '@/stores/notification-store';

/**
 * 비밀번호 재설정 (메일 링크 클릭 후 도달).
 * - searchParams.token이 필수. 토큰 만료 시 E0053.
 */
export default function ResetPasswordPage() {
  const router = useRouter();
  const sp = useSearchParams();
  const token = sp?.get('token') ?? '';
  const [serverError, setServerError] = useState<string | null>(null);

  const form = useForm<ResetPasswordForm>({
    resolver: zodResolver<ResetPasswordForm>(resetPasswordSchema),
    defaultValues: { token, password: '', password_confirm: '' },
  });
  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = form;

  const pwd = watch('password') ?? '';
  const checks = evaluatePassword(pwd);

  const onSubmit = handleSubmit(async () => {
    setServerError(null);
    try {
      await new Promise((r) => setTimeout(r, 400));
      toast.success('비밀번호가 변경되었습니다.');
      router.push(`${ROUTES.LOGIN}?reset=ok`);
    } catch (err) {
      if (!applyFieldErrors<ResetPasswordForm>(err, setError)) {
        setServerError(toUserMessage(err));
      }
    }
  });

  if (!token) {
    return (
      <main className="center" style={{ minHeight: '100vh', padding: 'var(--space-6)' }}>
        <div className="card" style={{ width: '100%', maxWidth: 420 }}>
          <div className="card__body stack gap-3">
            <ErrorCard
              title="잘못된 접근입니다."
              message="재설정 링크를 통해 다시 접속해주세요."
              code="E0053"
            />
            <Link href={ROUTES.FORGOT_PASSWORD}>
              <Button variant="primary" block>재설정 메일 다시 받기</Button>
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="center" style={{ minHeight: '100vh', padding: 'var(--space-6)' }}>
      <form onSubmit={onSubmit} className="card" style={{ width: '100%', maxWidth: 460 }} noValidate>
        <header className="card__header">
          <h1 className="card__title">새 비밀번호 설정</h1>
          <p className="card__subtitle">8~32자, 영문+숫자+특수문자 조합으로 입력하세요.</p>
        </header>
        <div className="card__body stack gap-4">
          <input type="hidden" {...register('token')} />

          <Field label="새 비밀번호" required error={errors.password?.message}>
            <Input
              type="password"
              leftIcon={<KeyRound className="h-4 w-4" />}
              autoComplete="new-password"
              error={!!errors.password}
              {...register('password')}
            />
          </Field>

          <ul className="stack gap-1 text-xs" aria-live="polite">
            <PolicyItem ok={checks.length} text="8~32자 길이" />
            <PolicyItem ok={checks.alpha} text="영문 포함" />
            <PolicyItem ok={checks.digit} text="숫자 포함" />
            <PolicyItem ok={checks.special} text="특수문자 포함" />
          </ul>

          <Field label="비밀번호 확인" required error={errors.password_confirm?.message}>
            <Input
              type="password"
              leftIcon={<KeyRound className="h-4 w-4" />}
              autoComplete="new-password"
              error={!!errors.password_confirm}
              {...register('password_confirm')}
            />
          </Field>

          {serverError && <ErrorCard message={serverError} />}
        </div>
        <footer className="card__footer row items-center justify-between">
          <Link href={ROUTES.LOGIN} className="text-sm" style={{ color: 'var(--color-brand-300)' }}>
            로그인 화면으로
          </Link>
          <Button type="submit" variant="primary" loading={isSubmitting}>
            비밀번호 변경
          </Button>
        </footer>
      </form>
    </main>
  );
}

function PolicyItem({ ok, text }: { ok: boolean; text: string }) {
  return (
    <li className={cn('row items-center gap-2', ok ? 'text-up' : 'text-subtle')}>
      {ok ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
      <span>{text}</span>
    </li>
  );
}
