'use client';

/**
 * Toast — 일시적 알림 메시지.
 *
 * 실제 토스트 시스템은 Phase 1-B에서 sonner를 채택 예정.
 * 본 단계에서는 단일 Toast 컴포넌트와 ToastProvider 골격만 제공.
 *
 * a11y: type=danger 시 role=alert, 그 외 role=status.
 */
import { CheckCircle2, Info, TriangleAlert, XCircle, X } from 'lucide-react';
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { cn } from '../../lib/cn';
import { Icon } from '../atoms/Icon';

export type ToastType = 'success' | 'warning' | 'danger' | 'info';

export interface ToastItem {
  id: string;
  type?: ToastType;
  title: ReactNode;
  description?: ReactNode;
  /** 자동 사라짐 (ms) — 0이면 수동 닫기만 */
  duration?: number;
}

interface ToastContextValue {
  toasts: ToastItem[];
  show: (toast: Omit<ToastItem, 'id'>) => string;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const typeIcon = {
  success: CheckCircle2,
  warning: TriangleAlert,
  danger: XCircle,
  info: Info,
} as const;

const typeStyles: Record<ToastType, string> = {
  success: 'border-success-50 bg-success-50 text-success',
  warning: 'border-warning-50 bg-warning-50 text-warning',
  danger: 'border-danger-50 bg-danger-50 text-danger',
  info: 'border-info-50 bg-info-50 text-info',
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback(
    (toast: Omit<ToastItem, 'id'>) => {
      const id =
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random()}`;
      const item: ToastItem = { id, duration: 4000, ...toast };
      setToasts((prev) => [...prev, item]);
      if (item.duration && item.duration > 0) {
        setTimeout(() => dismiss(id), item.duration);
      }
      return id;
    },
    [dismiss],
  );

  const value = useMemo(() => ({ toasts, show, dismiss }), [toasts, show, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastViewport />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast는 <ToastProvider> 내부에서만 사용 가능합니다.');
  return ctx;
}

function ToastViewport() {
  const { toasts, dismiss } = useToast();
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed bottom-4 right-4 z-toast flex flex-col gap-2"
    >
      {toasts.map((t) => (
        <Toast key={t.id} item={t} onClose={() => dismiss(t.id)} />
      ))}
    </div>
  );
}

function Toast({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  const type = item.type ?? 'info';
  const IconComp = typeIcon[type];
  return (
    <div
      role={type === 'danger' ? 'alert' : 'status'}
      className={cn(
        'pointer-events-auto flex w-80 items-start gap-3 rounded-lg border bg-surface-card p-3 shadow-md',
        typeStyles[type],
      )}
    >
      <Icon as={IconComp} size="md" />
      <div className="flex-1 text-neutral-900">
        <div className="text-[14px] font-semibold">{item.title}</div>
        {item.description && (
          <div className="mt-0.5 text-[13px] text-neutral-700">{item.description}</div>
        )}
      </div>
      <button
        type="button"
        aria-label="닫기"
        onClick={onClose}
        className="rounded p-0.5 text-neutral-500 hover:bg-neutral-100 focus-visible:outline-none focus-visible:shadow-focus"
      >
        <Icon as={X} size="sm" />
      </button>
    </div>
  );
}
