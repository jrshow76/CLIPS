import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export type ButtonVariant = 'default' | 'primary' | 'danger' | 'success' | 'ghost' | 'outline';
export type ButtonSize = 'sm' | 'md' | 'lg' | 'icon';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const variantClass: Record<ButtonVariant, string> = {
  default: '',
  primary: 'btn--primary',
  danger: 'btn--danger',
  success: 'btn--success',
  ghost: 'btn--ghost',
  outline: 'btn--outline',
};

const sizeClass: Record<ButtonSize, string> = {
  sm: 'btn--sm',
  md: '',
  lg: 'btn--lg',
  icon: 'btn--icon',
};

/**
 * Designer BEM `.btn` 1:1 매핑 버튼.
 * - variant: primary/danger/success/ghost/outline
 * - size: sm/md/lg/icon
 * - loading: 클릭 비활성 + 좌측 스피너
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'default', size = 'md', block, loading, leftIcon, rightIcon, className, children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cn('btn', variantClass[variant], sizeClass[size], block && 'btn--block', className)}
      disabled={disabled || loading}
      aria-disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Spinner /> : leftIcon}
      {children}
      {rightIcon}
    </button>
  );
});

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-r-transparent"
    />
  );
}
