'use client';

import { AtSign, KeyRound } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { ErrorCard } from '@/components/ui/error-card';
import { Field, Input } from '@/components/ui/input';
import { useLogin } from '@/lib/api/queries/auth';
import { ROUTES } from '@/lib/constants';

/**
 * 로그인 페이지 - Designer login.html 마크업 React 변환.
 * - 좌: 브랜드 히어로, 우: 로그인 폼
 * - 인증 실패 시 .error-card로 메시지 노출
 */
export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login.mutateAsync({ email, password });
      router.push(ROUTES.DASHBOARD);
    } catch (err) {
      const e = err as { code?: string; userMessage?: string; message: string };
      setError(`${e.userMessage ?? e.message}${e.code ? ` (${e.code})` : ''}`);
    }
  }

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
            <Badge variant="sim" dot>
              SIM 우선
            </Badge>
            <Badge variant="success" dot>
              한도 자동 검증
            </Badge>
            <Badge variant="info" dot>
              실시간 알림
            </Badge>
          </div>
        </div>
        <p className="auth__footer">
          © 2026 TradePilot · 본 서비스는 투자 자문이 아닙니다. 매매 결정은 사용자 본인 책임입니다.
        </p>
      </section>

      <section className="auth__form-wrap">
        <form onSubmit={onSubmit} className="auth__form stack gap-5">
          <header className="stack gap-1">
            <h1 className="h2">로그인</h1>
            <p className="text-sm text-muted">시뮬레이션 모드로 안전하게 시작합니다.</p>
          </header>

          <Field label="이메일" htmlFor="email">
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@trade.com"
              leftIcon={<AtSign className="h-4 w-4" />}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </Field>

          <Field label="비밀번호" htmlFor="password" hint="대소문자 구분, 5회 연속 실패 시 15분 잠금">
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="8~32자 영문+숫자+특수문자"
              leftIcon={<KeyRound className="h-4 w-4" />}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Field>

          <div className="row items-center justify-between">
            <Checkbox checked={remember} onChange={setRemember} label="자동 로그인" />
            <Link href={ROUTES.PASSWORD_RESET} className="text-sm" style={{ color: 'var(--color-brand-300)' }}>
              비밀번호 재설정
            </Link>
          </div>

          <Button type="submit" variant="primary" size="lg" block loading={login.isPending}>
            로그인
          </Button>

          {error && (
            <ErrorCard title="이메일 또는 비밀번호가 올바르지 않습니다." message={error} />
          )}

          <div className="divider" />

          <p className="text-sm text-muted center">
            아직 계정이 없으신가요?
            <Link href={ROUTES.SIGNUP} style={{ color: 'var(--color-brand-300)', marginLeft: 6 }}>
              회원가입
            </Link>
          </p>

          <p className="text-xs text-subtle center">
            단축키 <span className="kbd">Enter</span> 로 로그인
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
        .auth__brand {
          display: flex;
          align-items: center;
          gap: 12px;
          font-weight: var(--fw-bold);
          font-size: var(--fs-20);
        }
        .auth__brand-mark {
          width: 36px;
          height: 36px;
          border-radius: 10px;
          background: linear-gradient(135deg, var(--color-brand-400), var(--color-brand-600));
          display: grid;
          place-items: center;
          color: #fff;
        }
        .auth__hero-title {
          font-size: var(--fs-32);
          font-weight: var(--fw-bold);
          line-height: 1.2;
          letter-spacing: -0.02em;
          max-width: 480px;
        }
        .auth__hero-desc {
          color: var(--color-text-2);
          margin-top: var(--space-3);
          max-width: 480px;
        }
        .auth__chips {
          display: flex;
          gap: var(--space-2);
          flex-wrap: wrap;
          margin-top: var(--space-6);
        }
        .auth__footer {
          font-size: var(--fs-12);
          color: var(--color-text-3);
        }
        .auth__form-wrap {
          display: flex;
          align-items: center;
          justify-content: center;
          padding: var(--space-12);
        }
        .auth__form {
          width: 100%;
          max-width: 380px;
        }
        @media (max-width: 1024px) {
          .auth-root {
            grid-template-columns: 1fr;
          }
          .auth__hero {
            padding: var(--space-8);
            min-height: 280px;
          }
        }
      `}</style>
    </main>
  );
}
