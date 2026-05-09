'use client';

import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary:
    'bg-[#F97316] text-white hover:bg-[#EA580C] disabled:bg-[#F97316]/50',
  secondary:
    'bg-white text-[#78716C] border border-[#E7E5E4] hover:bg-[#F5F5F0] disabled:opacity-50',
  danger:
    'bg-white text-[#DC2626] border border-[#FCA5A5] hover:bg-red-50 disabled:opacity-50',
  ghost:
    'bg-transparent text-[#78716C] border border-[#E7E5E4] hover:bg-[#F5F5F0] disabled:opacity-50',
};

const sizeClasses: Record<Size, string> = {
  sm: 'px-3.5 py-1.5 text-[13px] font-semibold rounded-lg',
  md: 'px-4 py-2.5 text-[14px] font-semibold rounded-[10px]',
  lg: 'px-5 py-3.5 text-[15px] font-bold rounded-[10px]',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      fullWidth = false,
      className,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          'inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer',
          variantClasses[variant],
          sizeClasses[size],
          fullWidth && 'w-full',
          (disabled || loading) && 'cursor-not-allowed',
          className
        )}
        {...props}
      >
        {loading && (
          <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
