/**
 * Spinner — 로딩 인디케이터.
 * 사이즈: xs(12) / sm(16) / md(20) / lg(24).
 */
import { type HTMLAttributes } from 'react';

import { cn } from '../../lib/cn';

export interface SpinnerProps extends HTMLAttributes<HTMLSpanElement> {
  size?: 'xs' | 'sm' | 'md' | 'lg';
  /** 접근성 라벨 (스크린리더) */
  label?: string;
}

const sizeMap = {
  xs: 'h-3 w-3 border',
  sm: 'h-4 w-4 border',
  md: 'h-5 w-5 border-2',
  lg: 'h-6 w-6 border-2',
};

export function Spinner({ className, size = 'md', label = '로딩 중', ...rest }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-live="polite"
      aria-label={label}
      className={cn(
        'inline-block animate-spin rounded-full border-current border-t-transparent text-current',
        sizeMap[size],
        className,
      )}
      {...rest}
    />
  );
}
