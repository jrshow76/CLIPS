/**
 * EmptyState — 검색 결과 없음 / 빈 목록 자리표시자 (DSN-03 §4.10)
 */
import { type ReactNode } from 'react';

import { cn } from '../../lib/cn';

export interface EmptyStateProps {
  /** Lucide icon 등 */
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  /** 주요 액션 슬롯 */
  primaryAction?: ReactNode;
  /** 보조 액션 */
  secondaryAction?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  primaryAction,
  secondaryAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className={cn(
        'flex flex-col items-center justify-center gap-3 px-6 py-12 text-center text-neutral-600',
        className,
      )}
    >
      {icon && <div className="text-neutral-400">{icon}</div>}
      <h3 className="text-h3 text-neutral-900">{title}</h3>
      {description && <p className="max-w-md text-[14px]">{description}</p>}
      {(primaryAction || secondaryAction) && (
        <div className="mt-2 flex items-center gap-2">
          {primaryAction}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}
