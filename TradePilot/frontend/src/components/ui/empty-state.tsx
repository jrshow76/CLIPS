import { type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon = '★', title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('empty-state', className)}>
      <div className="empty-state__icon" aria-hidden="true">
        {icon}
      </div>
      <p className="empty-state__title">{title}</p>
      {description && <p className="empty-state__desc">{description}</p>}
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  );
}
