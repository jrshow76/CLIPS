import { type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface KpiProps {
  label: ReactNode;
  value: ReactNode;
  delta?: ReactNode;
  deltaClassName?: string;
  className?: string;
}

export function Kpi({ label, value, delta, deltaClassName, className }: KpiProps) {
  return (
    <div className={cn('kpi', className)}>
      <span className="kpi__label">{label}</span>
      <span className="kpi__value">{value}</span>
      {delta && <span className={cn('kpi__delta', deltaClassName)}>{delta}</span>}
    </div>
  );
}
