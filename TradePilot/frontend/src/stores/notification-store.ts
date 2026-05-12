import { create } from 'zustand';
import { v4 as uuid } from 'uuid';

export type ToastVariant = 'info' | 'success' | 'warning' | 'danger';

export interface Toast {
  id: string;
  variant: ToastVariant;
  title: string;
  message?: string;
  duration?: number; // ms
}

interface NotificationState {
  toasts: Toast[];
  push: (toast: Omit<Toast, 'id'>) => string;
  dismiss: (id: string) => void;
  clear: () => void;
}

/**
 * 토스트 큐 스토어.
 * - 사용 예: `useNotificationStore.getState().push({ variant: 'success', title: '주문 접수' })`
 * - 페이지 전역에 `<Toaster />`(components/ui/toaster.tsx)를 마운트해 표시.
 */
export const useNotificationStore = create<NotificationState>((set, get) => ({
  toasts: [],
  push: (toast) => {
    const id = uuid();
    const next: Toast = { id, duration: 4000, ...toast };
    set({ toasts: [...get().toasts, next] });
    if (typeof window !== 'undefined' && next.duration && next.duration > 0) {
      window.setTimeout(() => get().dismiss(id), next.duration);
    }
    return id;
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
  clear: () => set({ toasts: [] }),
}));

/** 짧은 헬퍼 */
export const toast = {
  info: (title: string, message?: string) =>
    useNotificationStore.getState().push({ variant: 'info', title, message }),
  success: (title: string, message?: string) =>
    useNotificationStore.getState().push({ variant: 'success', title, message }),
  warning: (title: string, message?: string) =>
    useNotificationStore.getState().push({ variant: 'warning', title, message }),
  danger: (title: string, message?: string) =>
    useNotificationStore.getState().push({ variant: 'danger', title, message }),
};
