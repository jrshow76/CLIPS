import { type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface StatRowProps {
  label: ReactNode;
  value: ReactNode;
  valueClassName?: string;
  className?: string;
}

export function StatRow({ label, value, valueClassName, className }: StatRowProps) {
  return (
    <div className={cn('stat-row', className)}>
      <span className="stat-row__label">{label}</span>
      <span className={cn('stat-row__value', valueClassName)}>{value}</span>
    </div>
  );
}
