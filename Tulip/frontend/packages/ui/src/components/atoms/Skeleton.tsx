/**
 * Skeleton — 로딩 자리표시 (DSN-03 §3.9).
 *
 * Variants: text / circle / rect
 * `prefers-reduced-motion` 시 정적.
 */
import { cn } from '../../lib/cn';

export interface SkeletonProps {
  variant?: 'text' | 'circle' | 'rect';
  width?: number | string;
  height?: number | string;
  className?: string;
}

export function Skeleton({ variant = 'rect', width, height, className }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      style={{ width, height }}
      className={cn(
        'inline-block bg-neutral-200 motion-safe:animate-pulse',
        variant === 'text' && 'h-3 rounded',
        variant === 'circle' && 'rounded-full',
        variant === 'rect' && 'rounded-md',
        className,
      )}
    />
  );
}
