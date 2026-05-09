/**
 * Button 공통 컴포넌트
 * Designer common.css 클래스 기반: .btn, .btn--primary/secondary/ghost/danger, .btn--sm/lg/xl
 */

import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'default' | 'lg' | 'xl'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  /** 로딩 상태: 버튼 비활성화 + 스피너 표시 */
  loading?: boolean
  /** 너비 100% */
  fullWidth?: boolean
  /** 완전 원형 */
  round?: boolean
  children: ReactNode
}

const variantClassMap: Record<ButtonVariant, string> = {
  primary: 'btn--primary',
  secondary: 'btn--secondary',
  ghost: 'btn--ghost',
  danger: 'btn--danger',
}

const sizeClassMap: Record<ButtonSize, string> = {
  sm: 'btn--sm',
  default: '',
  lg: 'btn--lg',
  xl: 'btn--xl',
}

export function Button({
  variant = 'primary',
  size = 'default',
  loading = false,
  fullWidth = false,
  round = false,
  disabled,
  className = '',
  children,
  ...props
}: ButtonProps) {
  const classes = [
    'btn',
    variantClassMap[variant],
    sizeClassMap[size],
    fullWidth ? 'btn--full' : '',
    round ? 'btn--round' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <button
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading}
      {...props}
    >
      {loading && (
        <svg
          className="btn-spinner"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
          style={{
            animation: 'spin 0.75s linear infinite',
          }}
        >
          <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
          <path d="M12 2a10 10 0 0 1 10 10" />
        </svg>
      )}
      {children}
    </button>
  )
}
