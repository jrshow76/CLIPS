'use client';

import { AlertCircle, CheckCircle2, Info, X, AlertTriangle } from 'lucide-react';

import { Button } from './button';
import { cn } from '@/lib/utils/cn';
import { useNotificationStore, type ToastVariant } from '@/stores/notification-store';

const variantIcon: Record<ToastVariant, React.ReactNode> = {
  info: <Info className="text-info h-4 w-4" />,
  success: <CheckCircle2 className="text-success h-4 w-4" />,
  warning: <AlertTriangle className="text-warning h-4 w-4" />,
  danger: <AlertCircle className="text-danger h-4 w-4" />,
};

const variantClass: Record<ToastVariant, string> = {
  info: '',
  success: 'toast--success',
  warning: 'toast--warning',
  danger: 'toast--danger',
};

/**
 * 전역 토스트 출력기. AppShell layout에 한 번만 마운트.
 */
export function Toaster() {
  const toasts = useNotificationStore((s) => s.toasts);
  const dismiss = useNotificationStore((s) => s.dismiss);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-region" role="region" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={cn('toast', variantClass[t.variant])}>
          <span className="mt-0.5">{variantIcon[t.variant]}</span>
          <div className="flex-1">
            <div className="toast__title">{t.title}</div>
            {t.message && <div className="toast__msg">{t.message}</div>}
          </div>
          <Button variant="ghost" size="icon" onClick={() => dismiss(t.id)} aria-label="닫기">
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      ))}
    </div>
  );
}
