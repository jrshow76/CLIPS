'use client';

import { AtSign, CheckCircle2, KeyRound, User2, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { ErrorCard } from '@/components/ui/error-card';
import { Field, Input } from '@/components/ui/input';
import { useSignup } from '@/lib/api/queries/auth';
import { ROUTES } from '@/lib/constants';
import { applyFieldErrors, toUserMessage } from '@/lib/forms/extract-field-errors';
import { evaluatePassword, signupFormSchema, type SignupForm } from '@/lib/forms/zod-schemas';
import { zodResolver } from '@/lib/forms/zod-resolver';
import { cn } from '@/lib/utils/cn';

/**
 * 회원가입 페이지 - 강화 버전.
 * - react-hook-form + zod 검증, 한글 메시지.
 * - 비밀번호 정책 실시간 체크리스트 표시.
 * - 약관 동의 체크박스(필수 2종).
 */
export default function SignupPage() {
  const router = useRouter();
  const signup = useSignup();
  const [serverError, setServerError] = useState<string | null>(null);

  const form = useForm<SignupForm>({
    resolver: zodResolver<SignupForm>(signupFormSchema),
    mode: 'onBlur',
    defaultValues: {
      email: '',
      nickname: '',
      password: '',
      password_confirm: '',
      agree_terms: false,
      agree_privacy: false,
    },
  });
  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = form;

  const pwd = watch('password') ?? '';
  const checks = evaluatePassword(pwd);

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      await signup.mutateAsync({
        email: values.email,
        password: values.password,
        nickname: values.nickname,
      });
      router.push(`${ROUTES.LOGIN}?signup=ok`);
    } catch (err) {
      if (!applyFieldErrors<SignupForm>(err, setError)) {
        setServerError(toUserMessage(err));
      }
    }
  });

  return (
    <main className="center" style={{ minHeight: '100vh', padding: 'var(--space-6)' }}>
      <form onSubmit={onSubmit} className="card" style={{ width: '100%', maxWidth: 460 }} noValidate>
        <header className="card__header">
          <h1 className="card__title">회원가입</h1>
          <p className="card__subtitle">시뮬레이션 모드로 안전하게 시작합니다.</p>
        </header>
        <div className="card__body stack gap-4">
          <Field label="이메일" htmlFor="email" required error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              leftIcon={<AtSign className="h-4 w-4" />}
              placeholder="you@trade.com"
              autoComplete="email"
              {...register('email')}
              error={!!errors.email}
            />
          </Field>

          <Field label="닉네임" htmlFor="nickname" required error={errors.nickname?.message}>
            <Input
              id="nickname"
              leftIcon={<User2 className="h-4 w-4" />}
              placeholder="2~16자"
              {...register('nickname')}
              error={!!errors.nickname}
            />
          </Field>

          <Field label="비밀번호" htmlFor="password" required error={errors.password?.message}>
            <Input
              id="password"
              type="password"
              leftIcon={<KeyRound className="h-4 w-4" />}
              placeholder="8~32자, 영문+숫자+특수문자"
              autoComplete="new-password"
              {...register('password')}
              error={!!errors.password}
            />
          </Field>

          {/* 비밀번호 정책 체크리스트 */}
          <ul className="stack gap-1 text-xs" aria-live="polite">
            <PolicyItem ok={checks.length} text="8~32자 길이" />
            <PolicyItem ok={checks.alpha} text="영문 포함" />
            <PolicyItem ok={checks.digit} text="숫자 포함" />
            <PolicyItem ok={checks.special} text="특수문자 포함" />
          </ul>

          <Field
            label="비밀번호 확인"
            htmlFor="password_confirm"
            required
            error={errors.password_confirm?.message}
          >
            <Input
              id="password_confirm"
              type="password"
              leftIcon={<KeyRound className="h-4 w-4" />}
              autoComplete="new-password"
              {...register('password_confirm')}
              error={!!errors.password_confirm}
            />
          </Field>

          <div className="stack gap-2">
            <Checkbox
              checked={watch('agree_terms')}
              onChange={(v) => setValue('agree_terms', v, { shouldValidate: true })}
              label={
                <span className="text-sm">
                  <Link href="/terms" className="underline" style={{ color: 'var(--color-brand-300)' }}>
                    이용약관
                  </Link>
                  에 동의합니다. (필수)
                </span>
              }
            />
            {errors.agree_terms?.message && (
              <span className="field__error">{errors.agree_terms.message}</span>
            )}
            <Checkbox
              checked={watch('agree_privacy')}
              onChange={(v) => setValue('agree_privacy', v, { shouldValidate: true })}
              label={
                <span className="text-sm">
                  <Link href="/privacy" className="underline" style={{ color: 'var(--color-brand-300)' }}>
                    개인정보 처리방침
                  </Link>
                  에 동의합니다. (필수)
                </span>
              }
            />
            {errors.agree_privacy?.message && (
              <span className="field__error">{errors.agree_privacy.message}</span>
            )}
          </div>

          {serverError && <ErrorCard title="가입 실패" message={serverError} />}
        </div>
        <footer className="card__footer row items-center justify-between">
          <Link href={ROUTES.LOGIN} className="text-sm" style={{ color: 'var(--color-brand-300)' }}>
            이미 계정이 있나요?
          </Link>
          <Button type="submit" variant="primary" loading={isSubmitting || signup.isPending}>
            가입하기
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
