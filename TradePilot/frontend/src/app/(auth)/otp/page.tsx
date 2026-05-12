'use client';

import { ShieldCheck, Timer } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

import { Banner } from '@/components/ui/banner';
import { Button } from '@/components/ui/button';
import { ErrorCard } from '@/components/ui/error-card';
import { ROUTES } from '@/lib/constants';
import { cn } from '@/lib/utils/cn';
import { toast } from '@/stores/notification-store';

/**
 * OTP 입력 화면 (6자리, 5분 타이머).
 * - LIVE 모드 전환 직전, 또는 비밀번호 재설정 후 호출.
 * - searchParams.purpose = 'live' | 'reset' | 'login' 으로 검증 후 처리.
 *
 * 백엔드 API: POST /auth/otp/verify { otp, purpose } → 토큰 or success.
 */
const TOTAL = 5 * 60; // 5분

export default function OtpPage() {
  const router = useRouter();
  const sp = useSearchParams();
  const purpose = (sp?.get('purpose') ?? 'login') as 'live' | 'reset' | 'login';

  const [digits, setDigits] = useState<string[]>(Array(6).fill(''));
  const [left, setLeft] = useState(TOTAL);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputsRef = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (left <= 0) return;
    const t = window.setInterval(() => setLeft((s) => s - 1), 1000);
    return () => window.clearInterval(t);
  }, [left]);

  useEffect(() => {
    inputsRef.current[0]?.focus();
  }, []);

  const expired = left <= 0;
  const otp = digits.join('');
  const filled = otp.length === 6;

  function onChange(idx: number, value: string) {
    const v = value.replace(/[^0-9]/g, '').slice(0, 1);
    setDigits((arr) => {
      const next = [...arr];
      next[idx] = v;
      return next;
    });
    if (v && idx < 5) inputsRef.current[idx + 1]?.focus();
  }

  function onKeyDown(idx: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Backspace' && !digits[idx] && idx > 0) {
      inputsRef.current[idx - 1]?.focus();
    }
    if (e.key === 'ArrowLeft' && idx > 0) inputsRef.current[idx - 1]?.focus();
    if (e.key === 'ArrowRight' && idx < 5) inputsRef.current[idx + 1]?.focus();
  }

  function onPaste(e: React.ClipboardEvent<HTMLInputElement>) {
    const text = e.clipboardData.getData('text').replace(/[^0-9]/g, '').slice(0, 6);
    if (!text) return;
    e.preventDefault();
    const arr = text.split('').concat(Array(6 - text.length).fill(''));
    setDigits(arr.slice(0, 6));
    inputsRef.current[Math.min(text.length, 5)]?.focus();
  }

  async function onVerify() {
    if (!filled || expired) return;
    setBusy(true);
    setError(null);
    try {
      // Mock: 123456 통과
      await new Promise((r) => setTimeout(r, 400));
      if (process.env.NEXT_PUBLIC_USE_MOCK === 'true') {
        if (otp !== '123456') throw new Error('OTP가 일치하지 않습니다. (mock: 123456 사용)');
      }
      toast.success('OTP 인증 완료');
      router.push(purpose === 'live' ? ROUTES.SETTINGS : ROUTES.DASHBOARD);
    } catch (err) {
      setError(err instanceof Error ? err.message : '인증 실패');
    } finally {
      setBusy(false);
    }
  }

  function onResend() {
    setLeft(TOTAL);
    setDigits(Array(6).fill(''));
    inputsRef.current[0]?.focus();
    toast.info('OTP를 재발급했습니다.');
  }

  const mm = String(Math.floor(left / 60)).padStart(2, '0');
  const ss = String(left % 60).padStart(2, '0');

  return (
    <main className="center" style={{ minHeight: '100vh', padding: 'var(--space-6)' }}>
      <div className="card" style={{ width: '100%', maxWidth: 460 }}>
        <header className="card__header">
          <div className="row items-center gap-2">
            <ShieldCheck className="text-brand h-5 w-5" />
            <h1 className="card__title">OTP 인증</h1>
          </div>
          <p className="card__subtitle">
            {purpose === 'live'
              ? '실거래 전환을 위해 6자리 OTP를 입력하세요.'
              : '인증 코드를 등록된 휴대폰으로 발송했습니다.'}
          </p>
        </header>
        <div className="card__body stack gap-4">
          <Banner variant={expired ? 'warning' : 'info'} icon={<Timer className="h-4 w-4" />}>
            {expired ? 'OTP가 만료되었습니다. 재발급 후 다시 시도하세요.' : `남은 시간 ${mm}:${ss}`}
          </Banner>

          <div className="row gap-2 justify-center">
            {digits.map((d, i) => (
              <input
                key={i}
                ref={(el) => {
                  inputsRef.current[i] = el;
                }}
                className={cn('input text-center')}
                style={{ width: 48, fontSize: 22, letterSpacing: 4 }}
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={1}
                value={d}
                onChange={(e) => onChange(i, e.target.value)}
                onKeyDown={(e) => onKeyDown(i, e)}
                onPaste={onPaste}
                aria-label={`OTP ${i + 1}번째 자리`}
              />
            ))}
          </div>

          {process.env.NEXT_PUBLIC_USE_MOCK === 'true' && (
            <p className="text-xs text-subtle center">데모: <span className="kbd">123456</span> 입력</p>
          )}

          {error && <ErrorCard message={error} />}

          <div className="row gap-2">
            <Button variant="outline" onClick={onResend} disabled={busy} block>
              재발송
            </Button>
            <Button variant="primary" onClick={onVerify} disabled={!filled || expired} loading={busy} block>
              인증 확인
            </Button>
          </div>
        </div>
        <footer className="card__footer">
          <Link href={ROUTES.LOGIN} className="text-sm" style={{ color: 'var(--color-brand-300)' }}>
            로그인 화면으로
          </Link>
        </footer>
      </div>
    </main>
  );
}
