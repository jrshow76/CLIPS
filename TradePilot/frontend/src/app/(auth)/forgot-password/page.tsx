'use client';

import { AtSign, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { Button } from '@/components/ui/button';
import { ErrorCard } from '@/components/ui/error-card';
import { Field, Input } from '@/components/ui/input';
import { ROUTES } from '@/lib/constants';
import { toUserMessage } from '@/lib/forms/extract-field-errors';
import { forgotPasswordSchema, type ForgotPasswordForm } from '@/lib/forms/zod-schemas';
import { zodResolver } from '@/lib/forms/zod-resolver';

/**
 * 비밀번호 찾기 (재설정 링크 발송).
 * - 입력 즉시 서버 메일 발송 → "메일 발송됨" 안내 화면.
 * - 실제 API: POST /auth/password/forgot { email }
 */
export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const form = useForm<ForgotPasswordForm>({
    resolver: zodResolver<ForgotPasswordForm>(forgotPasswordSchema),
    defaultValues: { email: '' },
  });
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = form;

  const onSubmit = handleSubmit(async () => {
    setServerError(null);
    try {
      // mock: 항상 성공
      await new Promise((r) => setTimeout(r, 400));
      setSent(true);
    } catch (err) {
      setServerError(toUserMessage(err));
    }
  });

  return (
    <main className="center" style={{ minHeight: '100vh', padding: 'var(--space-6)' }}>
      <div className="card" style={{ width: '100%', maxWidth: 420 }}>
        <header className="card__header">
          <h1 className="card__title">비밀번호 재설정</h1>
          <p className="card__subtitle">가입한 이메일로 재설정 링크를 보내드립니다.</p>
        </header>

        {sent ? (
          <div className="card__body stack gap-4">
            <div className="row items-start gap-3" style={{ background: 'var(--color-bg-2)', padding: 'var(--space-4)', borderRadius: 'var(--radius-md)' }}>
              <CheckCircle2 className="text-up h-5 w-5 mt-1 flex-none" />
              <div className="stack gap-1">
                <p className="text-strong fw-semibold">이메일이 발송되었습니다.</p>
                <p className="text-sm text-muted">
                  메일함을 확인하여 재설정 링크를 클릭하세요. 10분 내 사용 가능합니다.
                </p>
              </div>
            </div>
            <Link href={ROUTES.LOGIN}>
              <Button variant="primary" block>로그인으로 돌아가기</Button>
            </Link>
          </div>
        ) : (
          <form onSubmit={onSubmit} noValidate>
            <div className="card__body stack gap-4">
              <Field label="이메일" required error={errors.email?.message}>
                <Input
                  type="email"
                  autoComplete="email"
                  leftIcon={<AtSign className="h-4 w-4" />}
                  placeholder="you@trade.com"
                  error={!!errors.email}
                  {...register('email')}
                />
              </Field>
              {serverError && <ErrorCard message={serverError} />}
            </div>
            <footer className="card__footer row items-center justify-between">
              <Link href={ROUTES.LOGIN} className="text-sm" style={{ color: 'var(--color-brand-300)' }}>
                로그인 화면으로
              </Link>
              <Button type="submit" variant="primary" loading={isSubmitting}>
                재설정 메일 발송
              </Button>
            </footer>
          </form>
        )}
      </div>
    </main>
  );
}
