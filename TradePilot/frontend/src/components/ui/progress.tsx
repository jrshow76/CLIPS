import { cn } from '@/lib/utils/cn';

export interface ProgressProps {
  value: number; // 0~100
  variant?: 'default' | 'success' | 'danger';
  label?: string;
  className?: string;
}

export function Progress({ value, variant = 'default', label, className }: ProgressProps) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className={cn('stack gap-1', className)}>
      <div
        className={cn('progress', variant === 'success' && 'progress--success', variant === 'danger' && 'progress--danger')}
        role="progressbar"
        aria-valuenow={v}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div className="progress__bar" style={{ width: `${v}%` }} />
      </div>
      {label && (
        <div className="text-subtle text-xs">
          {label} {v.toFixed(0)}%
        </div>
      )}
    </div>
  );
}
