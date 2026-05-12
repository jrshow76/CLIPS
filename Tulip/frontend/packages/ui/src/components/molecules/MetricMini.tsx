/**
 * MetricMini — 좁은 공간용 작은 메트릭 (라벨 + 숫자)
 *
 * 사용처: 좌석 점유율 라인의 우측 항목, 카드 내부의 보조 지표.
 */
import { type ReactNode } from 'react';

import { cn } from '../../lib/cn';

export interface MetricMiniProps {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info';
  className?: string;
}

const TONE_VALUE: Record<NonNullable<MetricMiniProps['tone']>, string> = {
  neutral: 'text-neutral-900',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
  info: 'text-info',
};

export function MetricMini({
  label,
  value,
  hint,
  tone = 'neutral',
  className,
}: MetricMiniProps) {
  return (
    <div className={cn('inline-flex flex-col', className)}>
      <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
        {label}
      </span>
      <span className={cn('text-[18px] font-bold tabular-nums', TONE_VALUE[tone])}>{value}</span>
      {hint && <span className="text-[11px] text-neutral-500">{hint}</span>}
    </div>
  );
}
