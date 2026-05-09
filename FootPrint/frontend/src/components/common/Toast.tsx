'use client';

import { useToastStore, type Toast } from './useToast';
import { cn } from '@/lib/utils';

const typeConfig = {
  success: {
    icon: '✓',
    bg: 'bg-[#F0FDF4]',
    border: 'border-[#86EFAC]',
    text: 'text-[#16A34A]',
    iconBg: 'bg-[#16A34A]',
  },
  error: {
    icon: '✕',
    bg: 'bg-[#FEF2F2]',
    border: 'border-[#FCA5A5]',
    text: 'text-[#DC2626]',
    iconBg: 'bg-[#DC2626]',
  },
  info: {
    icon: 'i',
    bg: 'bg-[#F0F9FF]',
    border: 'border-[#7DD3FC]',
    text: 'text-[#0284C7]',
    iconBg: 'bg-[#0284C7]',
  },
};

function ToastItem({ toast }: { toast: Toast }) {
  const { removeToast } = useToastStore();
  const config = typeConfig[toast.type];

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg min-w-[280px] max-w-sm',
        config.bg,
        config.border
      )}
    >
      <span
        className={cn(
          'w-5 h-5 rounded-full flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0',
          config.iconBg
        )}
      >
        {config.icon}
      </span>
      <p className={cn('flex-1 text-[14px] font-medium', config.text)}>
        {toast.message}
      </p>
      <button
        onClick={() => removeToast(toast.id)}
        className={cn('text-[18px] leading-none opacity-60 hover:opacity-100 transition-opacity', config.text)}
      >
        ×
      </button>
    </div>
  );
}

export default function ToastContainer() {
  const { toasts } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  );
}
