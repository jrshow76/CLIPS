'use client';

/**
 * Button — 행위 트리거 (DSN-03 §3.1)
 *
 * Variants: primary / secondary / tertiary / ghost / danger / link
 * Sizes:    xs(24) / sm(32) / md(40) / lg(48)
 * a11y:     loading 시 aria-busy, focus-visible 포커스링, Enter/Space 키보드.
 */
import { cva, type VariantProps } from 'class-variance-authority';
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Spinner } from './Spinner';

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 whitespace-nowrap',
    'font-semibold transition-colors',
    'focus-visible:outline-none focus-visible:shadow-focus',
    'disabled:cursor-not-allowed disabled:opacity-50',
    'select-none',
  ].join(' '),
  {
    variants: {
      variant: {
        primary: 'bg-primary-500 text-white hover:bg-primary-600 active:bg-primary-700',
        secondary:
          'bg-neutral-100 text-neutral-900 border border-neutral-300 hover:bg-neutral-200',
        tertiary: 'bg-transparent text-primary-600 hover:bg-primary-50',
        ghost: 'bg-transparent text-neutral-700 hover:bg-neutral-100',
        danger: 'bg-danger text-white hover:opacity-90 active:opacity-80',
        link: 'bg-transparent text-primary-600 underline-offset-4 hover:underline px-0',
      },
      size: {
        xs: 'h-6 px-2 text-[12px] rounded-sm',
        sm: 'h-8 px-3 text-[13px] rounded-md',
        md: 'h-10 px-4 text-[14px] rounded-md',
        lg: 'h-12 px-5 text-[16px] rounded-md',
      },
      fullWidth: {
        true: 'w-full',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
      fullWidth: false,
    },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** 좌측 아이콘 (Lucide 등) */
  leftIcon?: ReactNode;
  /** 우측 아이콘 */
  rightIcon?: ReactNode;
  /** 로딩 상태 (자동 disabled, aria-busy) */
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    className,
    variant,
    size,
    fullWidth,
    leftIcon,
    rightIcon,
    loading = false,
    disabled,
    children,
    type = 'button',
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(buttonVariants({ variant, size, fullWidth }), className)}
      {...rest}
    >
      {loading ? (
        <Spinner size={size === 'lg' ? 'md' : 'sm'} aria-hidden="true" />
      ) : (
        leftIcon && <span className="inline-flex shrink-0">{leftIcon}</span>
      )}
      {children}
      {!loading && rightIcon && <span className="inline-flex shrink-0">{rightIcon}</span>}
    </button>
  );
});
