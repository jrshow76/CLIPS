import { useAppStore } from '../../store';
import type { ToastItem, ToastType } from '../../types';
import styles from './Toast.module.css';

// 토스트 타입별 아이콘 텍스트
const TOAST_ICONS: Record<ToastType, string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
};

// 개별 토스트 아이템 컴포넌트
function ToastItem({ toast }: { toast: ToastItem }) {
  const removeToast = useAppStore((state) => state.removeToast);

  return (
    <div className={`${styles.toast} ${styles[toast.type]}`} role="alert">
      <span className={styles.icon}>{TOAST_ICONS[toast.type]}</span>
      <span className={styles.message}>{toast.message}</span>
      <button
        className={styles.closeButton}
        onClick={() => removeToast(toast.id)}
        aria-label="닫기"
      >
        ×
      </button>
    </div>
  );
}

// 토스트 컨테이너 컴포넌트
export function ToastContainer() {
  const toasts = useAppStore((state) => state.toasts);

  if (toasts.length === 0) return null;

  return (
    <div className={styles.container} aria-live="polite">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  );
}
