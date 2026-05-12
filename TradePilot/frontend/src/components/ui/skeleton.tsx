import { cn } from '@/lib/utils/cn';

export interface SkeletonProps {
  className?: string;
  width?: number | string;
  height?: number | string;
  variant?: 'block' | 'text' | 'line';
}

export function Skeleton({ className, width, height, variant = 'block' }: SkeletonProps) {
  return (
    <span
      className={cn(
        'skeleton',
        variant === 'text' && 'skeleton--text',
        variant === 'line' && 'skeleton--line',
        'block',
        className,
      )}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}

/** 카드 본문 가짜 행 n개 */
export function SkeletonRows({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn('stack gap-3', className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} height={16} />
      ))}
    </div>
  );
}
