import { AlertTriangle } from 'lucide-react';
import { type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface ErrorCardProps {
  title?: string;
  message: string;
  code?: string;
  action?: ReactNode;
  className?: string;
}

export function ErrorCard({ title = '일시적인 오류가 발생했습니다.', message, code, action, className }: ErrorCardProps) {
  return (
    <div className={cn('error-card', className)} role="alert">
      <AlertTriangle className="text-danger mt-1 h-5 w-5 flex-none" aria-hidden="true" />
      <div className="flex-1">
        <p className="error-card__title">{title}</p>
        <p className="error-card__msg">
          {message}
          {code && <span className="text-subtle ml-2 text-xs">({code})</span>}
        </p>
        {action && <div className="mt-3">{action}</div>}
      </div>
    </div>
  );
}
