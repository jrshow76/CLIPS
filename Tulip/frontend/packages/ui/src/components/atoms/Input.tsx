/**
 * Input — 텍스트/이메일/숫자 등 (DSN-03 §3.3)
 *
 * Sizes: sm(32) / md(40) / lg(48)
 * States: default / focus / disabled / readonly / invalid
 * a11y: aria-invalid, aria-describedby(errorId) — FormField와 함께 사용 권장.
 */
import { cva, type VariantProps } from 'class-variance-authority';
import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';

import { cn } from '../../lib/cn';

const inputVariants = cva(
  [
    'flex w-full rounded-md border bg-surface-card text-neutral-900',
    'placeholder:text-neutral-500',
    'focus-visible:outline-none focus-visible:shadow-focus',
    'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-neutral-100',
    'read-only:bg-neutral-50',
    'transition-colors',
  ].join(' '),
  {
    variants: {
      size: {
        sm: 'h-8 px-2 text-[13px]',
        md: 'h-10 px-3 text-[14px]',
        lg: 'h-12 px-4 text-[16px]',
      },
      invalid: {
        true: 'border-danger focus-visible:border-danger',
        false: 'border-neutral-300 focus-visible:border-primary-500',
      },
    },
    defaultVariants: {
      size: 'md',
      invalid: false,
    },
  },
);

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size' | 'prefix'>,
    VariantProps<typeof inputVariants> {
  /** 좌측 접두 (아이콘 등) */
  prefix?: ReactNode;
  /** 우측 접미 */
  suffix?: ReactNode;
  /** 에러 여부 — true 시 aria-invalid="true" */
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, size, invalid, error, prefix, suffix, ...rest },
  ref,
) {
  const isInvalid = invalid ?? error ?? false;

  if (prefix || suffix) {
    return (
      <div
        className={cn(
          'flex items-center gap-2 rounded-md border border-neutral-300 bg-surface-card px-2',
          'focus-within:shadow-focus focus-within:border-primary-500',
          isInvalid && 'border-danger focus-within:border-danger',
          rest.disabled && 'opacity-50 cursor-not-allowed',
        )}
      >
        {prefix && <span className="flex shrink-0 text-neutral-500">{prefix}</span>}
        <input
          ref={ref}
          aria-invalid={isInvalid || undefined}
          className={cn(
            'flex-1 border-0 bg-transparent outline-none focus:outline-none focus:ring-0',
            'h-10 text-[14px] placeholder:text-neutral-500',
            'disabled:cursor-not-allowed',
            className,
          )}
          {...rest}
        />
        {suffix && <span className="flex shrink-0 text-neutral-500">{suffix}</span>}
      </div>
    );
  }

  return (
    <input
      ref={ref}
      aria-invalid={isInvalid || undefined}
      className={cn(inputVariants({ size, invalid: isInvalid }), className)}
      {...rest}
    />
  );
});
