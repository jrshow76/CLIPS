/**
 * 회원가입 페이지 (CSR)
 * API 요구사항 정의서 2.1 회원가입 기반
 * - 이메일, 비밀번호, 닉네임, 약관 동의 폼
 * - 클라이언트 사이드 유효성 검사 후 API 호출
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/common/Button'
import { useToast } from '@/components/common/Toast'
import { signup } from '@/lib/api/auth'
import type { SignupRequest } from '@/types/auth'

interface FormErrors {
  email?: string
  password?: string
  passwordConfirm?: string
  nickname?: string
  agreeTerms?: string
}

export default function SignupPage() {
  const router = useRouter()
  const toast = useToast()

  const [form, setForm] = useState<SignupRequest>({
    email: '',
    password: '',
    passwordConfirm: '',
    nickname: '',
    agreeTerms: false,
    agreePrivacy: false,
    agreeMarketing: false,
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [isLoading, setIsLoading] = useState(false)

  const PASSWORD_REGEX = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,20}$/
  const NICKNAME_REGEX = /^[가-힣a-zA-Z0-9_]{2,20}$/

  function validate(): boolean {
    const newErrors: FormErrors = {}

    if (!form.email) {
      newErrors.email = '이메일을 입력해주세요.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      newErrors.email = '올바른 이메일 형식을 입력하세요.'
    }

    if (!form.password) {
      newErrors.password = '비밀번호를 입력해주세요.'
    } else if (!PASSWORD_REGEX.test(form.password)) {
      newErrors.password = '비밀번호는 8~20자, 영문·숫자·특수문자를 포함해야 합니다.'
    }

    if (!form.passwordConfirm) {
      newErrors.passwordConfirm = '비밀번호 확인을 입력해주세요.'
    } else if (form.password !== form.passwordConfirm) {
      newErrors.passwordConfirm = '비밀번호가 일치하지 않습니다.'
    }

    if (!form.nickname) {
      newErrors.nickname = '닉네임을 입력해주세요.'
    } else if (!NICKNAME_REGEX.test(form.nickname)) {
      newErrors.nickname = '닉네임은 2~20자, 한글·영문·숫자·밑줄(_)만 사용 가능합니다.'
    }

    if (!form.agreeTerms || !form.agreePrivacy) {
      newErrors.agreeTerms = '필수 약관에 동의해야 합니다.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return

    setIsLoading(true)
    try {
      await signup(form)
      toast.success('회원가입이 완료되었습니다. 이메일을 확인해주세요.')
      router.push('/login')
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : '회원가입에 실패했습니다.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  function handleTextChange(field: keyof SignupRequest) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: e.target.value }))
      setErrors((prev) => ({ ...prev, [field]: undefined }))
    }
  }

  function handleCheckChange(field: keyof SignupRequest) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: e.target.checked }))
      if (field === 'agreeTerms' || field === 'agreePrivacy') {
        setErrors((prev) => ({ ...prev, agreeTerms: undefined }))
      }
    }
  }

  function handleAllAgree(e: React.ChangeEvent<HTMLInputElement>) {
    const checked = e.target.checked
    setForm((prev) => ({
      ...prev,
      agreeTerms: checked,
      agreePrivacy: checked,
      agreeMarketing: checked,
    }))
    setErrors((prev) => ({ ...prev, agreeTerms: undefined }))
  }

  const allAgreed = form.agreeTerms && form.agreePrivacy && form.agreeMarketing

  return (
    <div
      className="page-body"
      style={{
        display: 'flex',
        alignItems: 'flex-start',
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
        {/* 헤더 */}
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
            선반을 만들어볼까요?
          </h1>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-tertiary)' }}>
            무료로 시작하고 나만의 공간을 꾸미세요
          </p>
        </div>

        {/* 회원가입 폼 */}
        <form
          onSubmit={handleSubmit}
          noValidate
          aria-label="회원가입 폼"
          style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}
        >
          {/* 이메일 */}
          <div className="form-field">
            <label htmlFor="signup-email" className="form-label form-label--required">
              이메일
            </label>
            <input
              id="signup-email"
              type="email"
              className={`form-input ${errors.email ? 'form-input--error' : ''}`}
              placeholder="이메일 주소를 입력하세요"
              value={form.email}
              onChange={handleTextChange('email')}
              autoComplete="email"
              autoFocus
              aria-describedby={errors.email ? 'signup-email-error' : 'signup-email-hint'}
              aria-invalid={!!errors.email}
            />
            <span id="signup-email-hint" className="form-hint">
              가입 후 이메일 인증이 필요합니다.
            </span>
            {errors.email && (
              <span id="signup-email-error" className="form-error" role="alert">
                {errors.email}
              </span>
            )}
          </div>

          {/* 비밀번호 */}
          <div className="form-field">
            <label htmlFor="signup-password" className="form-label form-label--required">
              비밀번호
            </label>
            <input
              id="signup-password"
              type="password"
              className={`form-input ${errors.password ? 'form-input--error' : ''}`}
              placeholder="비밀번호를 입력하세요"
              value={form.password}
              onChange={handleTextChange('password')}
              autoComplete="new-password"
              aria-describedby={errors.password ? 'signup-password-error' : 'signup-password-hint'}
              aria-invalid={!!errors.password}
            />
            <span id="signup-password-hint" className="form-hint">
              8~20자, 영문·숫자·특수문자(!@#$%^&amp;*)를 포함해야 합니다.
            </span>
            {errors.password && (
              <span id="signup-password-error" className="form-error" role="alert">
                {errors.password}
              </span>
            )}
          </div>

          {/* 비밀번호 확인 */}
          <div className="form-field">
            <label htmlFor="signup-password-confirm" className="form-label form-label--required">
              비밀번호 확인
            </label>
            <input
              id="signup-password-confirm"
              type="password"
              className={`form-input ${errors.passwordConfirm ? 'form-input--error' : ''}`}
              placeholder="비밀번호를 다시 입력하세요"
              value={form.passwordConfirm}
              onChange={handleTextChange('passwordConfirm')}
              autoComplete="new-password"
              aria-describedby={errors.passwordConfirm ? 'signup-password-confirm-error' : undefined}
              aria-invalid={!!errors.passwordConfirm}
            />
            {errors.passwordConfirm && (
              <span id="signup-password-confirm-error" className="form-error" role="alert">
                {errors.passwordConfirm}
              </span>
            )}
          </div>

          {/* 닉네임 */}
          <div className="form-field">
            <label htmlFor="signup-nickname" className="form-label form-label--required">
              닉네임
            </label>
            <input
              id="signup-nickname"
              type="text"
              className={`form-input ${errors.nickname ? 'form-input--error' : ''}`}
              placeholder="닉네임을 입력하세요"
              value={form.nickname}
              onChange={handleTextChange('nickname')}
              maxLength={20}
              autoComplete="username"
              aria-describedby={errors.nickname ? 'signup-nickname-error' : 'signup-nickname-hint'}
              aria-invalid={!!errors.nickname}
            />
            <div
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            >
              <span id="signup-nickname-hint" className="form-hint">
                2~20자, 한글·영문·숫자·밑줄(_) 사용 가능
              </span>
              <span className={`form-counter ${form.nickname.length > 20 ? 'form-counter--over' : ''}`}>
                {form.nickname.length}/20
              </span>
            </div>
            {errors.nickname && (
              <span id="signup-nickname-error" className="form-error" role="alert">
                {errors.nickname}
              </span>
            )}
          </div>

          {/* 약관 동의 */}
          <div
            className="form-field"
            style={{
              background: 'var(--color-bg-muted)',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-4)',
              gap: 'var(--space-3)',
            }}
          >
            {/* 전체 동의 */}
            <label className="form-check" style={{ marginBottom: 'var(--space-3)', borderBottom: '1px solid var(--color-border-default)', paddingBottom: 'var(--space-3)' }}>
              <input
                type="checkbox"
                className="form-check__input"
                checked={allAgreed}
                onChange={handleAllAgree}
                aria-label="전체 약관 동의"
              />
              <span className="form-check__label" style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)' }}>
                전체 동의
              </span>
            </label>

            {/* 이용약관 (필수) */}
            <label className="form-check">
              <input
                type="checkbox"
                className="form-check__input"
                checked={form.agreeTerms}
                onChange={handleCheckChange('agreeTerms')}
                aria-label="이용약관 동의 (필수)"
                aria-required="true"
              />
              <span className="form-check__label">
                <span style={{ color: 'var(--color-error)', marginRight: 'var(--space-1)' }}>[필수]</span>
                이용약관 동의{' '}
                <Link href="/terms" style={{ color: 'var(--color-primary)' }} target="_blank">
                  보기
                </Link>
              </span>
            </label>

            {/* 개인정보처리방침 (필수) */}
            <label className="form-check">
              <input
                type="checkbox"
                className="form-check__input"
                checked={form.agreePrivacy}
                onChange={handleCheckChange('agreePrivacy')}
                aria-label="개인정보처리방침 동의 (필수)"
                aria-required="true"
              />
              <span className="form-check__label">
                <span style={{ color: 'var(--color-error)', marginRight: 'var(--space-1)' }}>[필수]</span>
                개인정보처리방침 동의{' '}
                <Link href="/privacy" style={{ color: 'var(--color-primary)' }} target="_blank">
                  보기
                </Link>
              </span>
            </label>

            {/* 마케팅 수신 동의 (선택) */}
            <label className="form-check">
              <input
                type="checkbox"
                className="form-check__input"
                checked={form.agreeMarketing}
                onChange={handleCheckChange('agreeMarketing')}
                aria-label="마케팅 수신 동의 (선택)"
              />
              <span className="form-check__label">
                <span style={{ color: 'var(--color-text-tertiary)', marginRight: 'var(--space-1)' }}>[선택]</span>
                마케팅 정보 수신 동의
              </span>
            </label>

            {errors.agreeTerms && (
              <span className="form-error" role="alert">
                {errors.agreeTerms}
              </span>
            )}
          </div>

          {/* 회원가입 버튼 */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            loading={isLoading}
            style={{ marginTop: 'var(--space-2)' }}
          >
            회원가입
          </Button>
        </form>

        {/* 로그인 링크 */}
        <p
          style={{
            textAlign: 'center',
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-tertiary)',
            marginTop: 'var(--space-6)',
          }}
        >
          이미 계정이 있으신가요?{' '}
          <Link
            href="/login"
            style={{ color: 'var(--color-primary)', fontWeight: 'var(--font-weight-semibold)' }}
          >
            로그인
          </Link>
        </p>
      </div>
    </div>
  )
}
