'use client';

import { AtSign, KeyRound } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { Badge } from '@/components/ui/badge';
import { Banner } from '@/components/ui/banner';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { ErrorCard } from '@/components/ui/error-card';
import { Field, Input } from '@/components/ui/input';
import { useLogin } from '@/lib/api/queries/auth';
import { ROUTES } from '@/lib/constants';
import { applyFieldErrors, toUserMessage } from '@/lib/forms/extract-field-errors';
import { loginFormSchema, type LoginForm } from '@/lib/forms/zod-schemas';
import { zodResolver } from '@/lib/forms/zod-resolver';

/**
 * 로그인 페이지 (강화 버전).
 * - react-hook-form + zod 검증.
 * - 가입 완료 후 redirect 시 ?signup=ok 배너 표시.
 */
export default function LoginPage() {
  const router = useRouter();
  const sp = useSearchParams();
  const justSignedUp = sp?.get('signup') === 'ok';
  const login = useLogin();
  const [serverError, setServerError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | undefined>();

  const form = useForm<LoginForm>({
    resolver: zodResolver<LoginForm>(loginFormSchema),
    mode: 'onSubmit',
    defaultValues: { email: '', password: '', remember: true },
  });
  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = form;

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    setErrorCode(undefined);
    try {
      await login.mutateAsync({ email: values.email, password: values.password });
      router.push(ROUTES.DASHBOARD);
    } catch (err) {
      if (!applyFieldErrors<LoginForm>(err, setError)) {
        setServerError(toUserMessage(err));
        if (err && typeof err === 'object' && 'code' in err) {
          setErrorCode(String((err as { code: string }).code));
        }
      }
    }
  });

  return (
    <main className="auth-root">
      <section className="auth__hero">
        <div className="auth__brand">
          <span className="auth__brand-mark">T</span>
          <span>TradePilot</span>
        </div>
        <div>
          <h2 className="auth__hero-title">
            전략 기반 자동매매,
            <br />
            안전한 시뮬레이션에서 시작하세요.
          </h2>
          <p className="auth__hero-desc">
            국내 주식 자동매매를 위한 통합 도구. AI 추천, 차트 분석, 백테스트, 리스크 한도까지 한 화면에서.
          </p>
          <div className="auth__chips">
            <Badge variant="sim" dot>SIM 우선</Badge>
            <Badge variant="success" dot>한도 자동 검증</Badge>
            <Badge variant="info" dot>실시간 알림</Badge>
          </div>
        </div>
        <p className="auth__footer">
          © 2026 TradePilot · 본 서비스는 투자 자문이 아닙니다. 매매 결정은 사용자 본인 책임입니다.
        </p>
      </section>

      <section className="auth__form-wrap">
        <form onSubmit={onSubmit} className="auth__form stack gap-5" noValidate>
          <header className="stack gap-1">
            <h1 className="h2">로그인</h1>
            <p className="text-sm text-muted">시뮬레이션 모드로 안전하게 시작합니다.</p>
          </header>

          {justSignedUp && (
            <Banner variant="info">가입이 완료되었습니다. 로그인하여 시작하세요.</Banner>
          )}

          <Field label="이메일" htmlFor="email" required error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@trade.com"
              leftIcon={<AtSign className="h-4 w-4" />}
              error={!!errors.email}
              {...register('email')}
            />
          </Field>

          <Field
            label="비밀번호"
            htmlFor="password"
            required
            error={errors.password?.message}
            hint="대소문자 구분, 5회 연속 실패 시 15분 잠금"
          >
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="8~32자 영문+숫자+특수문자"
              leftIcon={<KeyRound className="h-4 w-4" />}
              error={!!errors.password}
              {...register('password')}
            />
          </Field>

          <div className="row items-center justify-between">
            <Checkbox
              checked={watch('remember') ?? false}
              onChange={(v) => setValue('remember', v)}
              label="자동 로그인"
            />
            <Link href={ROUTES.FORGOT_PASSWORD} className="text-sm" style={{ color: 'var(--color-brand-300)' }}>
              비밀번호 재설정
            </Link>
          </div>

          <Button type="submit" variant="primary" size="lg" block loading={isSubmitting || login.isPending}>
            로그인
          </Button>

          {serverError && (
            <ErrorCard
              title="이메일 또는 비밀번호가 올바르지 않습니다."
              message={serverError}
              code={errorCode}
            />
          )}

          <div className="divider" />

          <p className="text-sm text-muted center">
            아직 계정이 없으신가요?
            <Link href={ROUTES.SIGNUP} style={{ color: 'var(--color-brand-300)', marginLeft: 6 }}>
              회원가입
            </Link>
          </p>
        </form>
      </section>

      <style jsx global>{`
        .auth-root {
          min-height: 100vh;
          display: grid;
          grid-template-columns: 1fr 1fr;
          background: var(--color-bg-0);
        }
        .auth__hero {
          position: relative;
          padding: var(--space-12);
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          color: #e6ebf2;
          background:
            radial-gradient(800px 400px at 30% 20%, rgba(47, 92, 255, 0.25), transparent 60%),
            radial-gradient(600px 400px at 70% 80%, rgba(239, 68, 68, 0.18), transparent 60%),
            linear-gradient(160deg, #0b0f17 0%, #131f59 100%);
        }
        .auth__brand { display: flex; align-items: center; gap: 12px; font-weight: var(--fw-bold); font-size: var(--fs-20); }
        .auth__brand-mark { width: 36px; height: 36px; border-radius: 10px; background: linear-gradient(135deg, var(--color-brand-400), var(--color-brand-600)); display: grid; place-items: center; color: #fff; }
        .auth__hero-title { font-size: var(--fs-32); font-weight: var(--fw-bold); line-height: 1.2; letter-spacing: -0.02em; max-width: 480px; }
        .auth__hero-desc { color: var(--color-text-2); margin-top: var(--space-3); max-width: 480px; }
        .auth__chips { display: flex; gap: var(--space-2); flex-wrap: wrap; margin-top: var(--space-6); }
        .auth__footer { font-size: var(--fs-12); color: var(--color-text-3); }
        .auth__form-wrap { display: flex; align-items: center; justify-content: center; padding: var(--space-12); }
        .auth__form { width: 100%; max-width: 380px; }
        @media (max-width: 1024px) {
          .auth-root { grid-template-columns: 1fr; }
          .auth__hero { padding: var(--space-8); min-height: 280px; }
        }
      `}</style>
    </main>
  );
}
