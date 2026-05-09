/**
 * 로그인 페이지 (CSR)
 * - React Hook Form 없이 controlled form으로 구현
 * - 로그인 성공 시 returnUrl 또는 홈으로 리다이렉트
 */

'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/common/Button'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/components/common/Toast'
import type { LoginRequest } from '@/types/auth'

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  )
}

function LoginContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login, isLoggedIn } = useAuth()
  const toast = useToast()

  const returnUrl = searchParams.get('returnUrl') ?? '/'

  const [form, setForm] = useState<LoginRequest>({ email: '', password: '' })
  const [errors, setErrors] = useState<Partial<LoginRequest>>({})
  const [isLoading, setIsLoading] = useState(false)

  // 이미 로그인된 경우 리다이렉트
  if (isLoggedIn) {
    router.replace(returnUrl)
    return null
  }

  function validate(): boolean {
    const newErrors: Partial<LoginRequest> = {}
    if (!form.email) {
      newErrors.email = '이메일을 입력해주세요.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      newErrors.email = '올바른 이메일 형식을 입력하세요.'
    }
    if (!form.password) {
      newErrors.password = '비밀번호를 입력해주세요.'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return

    setIsLoading(true)
    try {
      await login(form)
      toast.success('로그인되었습니다.')
      router.replace(returnUrl)
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : '로그인에 실패했습니다.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  function handleChange(field: keyof LoginRequest) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: e.target.value }))
      if (errors[field]) {
        setErrors((prev) => ({ ...prev, [field]: undefined }))
      }
    }
  }

  return (
    <div
      className="page-body"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: 'var(--space-8) var(--space-4)',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 'var(--container-sm)',
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
          borderRadius: 'var(--radius-2xl)',
          padding: 'var(--space-10)',
          boxShadow: 'var(--shadow-md)',
        }}
      >
        {/* 로고 */}
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-8)' }}>
          <Link
            href="/"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              textDecoration: 'none',
              marginBottom: 'var(--space-6)',
            }}
          >
            <div className="gnb__logo-mark" aria-hidden="true">S</div>
            <span className="gnb__logo-text">Shelfy</span>
          </Link>
          <h1
            style={{
              fontSize: 'var(--font-size-2xl)',
              fontWeight: 'var(--font-weight-bold)',
              marginBottom: 'var(--space-2)',
            }}
          >
            다시 만나서 반가워요
          </h1>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-tertiary)' }}>
            Shelfy 계정으로 로그인하세요
          </p>
        </div>

        {/* 로그인 폼 */}
        <form
          onSubmit={handleSubmit}
          noValidate
          aria-label="로그인 폼"
          style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}
        >
          {/* 이메일 */}
          <div className="form-field">
            <label htmlFor="login-email" className="form-label form-label--required">
              이메일
            </label>
            <input
              id="login-email"
              type="email"
              className={`form-input ${errors.email ? 'form-input--error' : ''}`}
              placeholder="이메일 주소를 입력하세요"
              value={form.email}
              onChange={handleChange('email')}
              autoComplete="email"
              autoFocus
              aria-describedby={errors.email ? 'login-email-error' : undefined}
              aria-invalid={!!errors.email}
            />
            {errors.email && (
              <span id="login-email-error" className="form-error" role="alert">
                {errors.email}
              </span>
            )}
          </div>

          {/* 비밀번호 */}
          <div className="form-field">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="login-password" className="form-label form-label--required">
                비밀번호
              </label>
              <Link
                href="/forgot-password"
                style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-primary)',
                }}
              >
                비밀번호를 잊으셨나요?
              </Link>
            </div>
            <input
              id="login-password"
              type="password"
              className={`form-input ${errors.password ? 'form-input--error' : ''}`}
              placeholder="비밀번호를 입력하세요"
              value={form.password}
              onChange={handleChange('password')}
              autoComplete="current-password"
              aria-describedby={errors.password ? 'login-password-error' : undefined}
              aria-invalid={!!errors.password}
            />
            {errors.password && (
              <span id="login-password-error" className="form-error" role="alert">
                {errors.password}
              </span>
            )}
          </div>

          {/* 로그인 버튼 */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            loading={isLoading}
            style={{ marginTop: 'var(--space-2)' }}
          >
            로그인
          </Button>
        </form>

        {/* 회원가입 링크 */}
        <p
          style={{
            textAlign: 'center',
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-tertiary)',
            marginTop: 'var(--space-6)',
          }}
        >
          아직 계정이 없으신가요?{' '}
          <Link
            href="/signup"
            style={{ color: 'var(--color-primary)', fontWeight: 'var(--font-weight-semibold)' }}
          >
            회원가입
          </Link>
        </p>
      </div>
    </div>
  )
}
