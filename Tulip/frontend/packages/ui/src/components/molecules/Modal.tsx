'use client';

/**
 * Modal / Dialog — 모달 다이얼로그 (DSN-03 §5.5)
 *
 * - 본 단계는 외부 의존 최소화를 위해 native HTMLDialogElement 사용.
 * - Phase 1-B에서 Radix UI Dialog 또는 react-aria로 교체 검토.
 *
 * a11y: role=dialog, focus trap (브라우저 내장), ESC 닫기, 백드롭 클릭 닫기.
 */
import { X } from 'lucide-react';
import { useEffect, useRef, type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Icon } from '../atoms/Icon';

export type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | 'full';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  description?: ReactNode;
  size?: ModalSize;
  /** 푸터 영역 (액션 버튼 등) */
  footer?: ReactNode;
  /** 백드롭 클릭 시 닫기 */
  closeOnBackdrop?: boolean;
  /** ESC 키로 닫기 */
  closeOnEsc?: boolean;
  /** X 닫기 버튼 표시 */
  hideCloseButton?: boolean;
  children?: ReactNode;
  className?: string;
}

const sizeMap: Record<ModalSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  full: 'max-w-[95vw] h-[95vh]',
};

export function Modal({
  open,
  onClose,
  title,
  description,
  size = 'md',
  footer,
  closeOnBackdrop = true,
  closeOnEsc = true,
  hideCloseButton,
  children,
  className,
}: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      try {
        dialog.showModal();
      } catch {
        // showModal 미지원 환경 fallback (없음 — 모든 모던 브라우저 지원)
      }
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  useEffect(() => {
    if (!closeOnEsc) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const handler = (e: Event) => {
      e.preventDefault();
      onClose();
    };
    dialog.addEventListener('cancel', handler);
    return () => dialog.removeEventListener('cancel', handler);
  }, [closeOnEsc, onClose]);

  function handleBackdropClick(e: React.MouseEvent<HTMLDialogElement>) {
    if (!closeOnBackdrop) return;
    // 백드롭은 dialog 자체, 컨텐츠 영역은 자식이므로 target===currentTarget 일 때만 닫음
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <dialog
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-title' : undefined}
      aria-describedby={description ? 'modal-desc' : undefined}
      onClick={handleBackdropClick}
      className={cn(
        'p-0 m-auto rounded-xl bg-surface-card text-neutral-900 shadow-xl backdrop:bg-black/50',
        'w-full',
        sizeMap[size],
        'animate-in fade-in zoom-in-95',
        className,
      )}
    >
      <div className="flex flex-col max-h-[85vh]">
        {(title || !hideCloseButton) && (
          <header className="flex items-start justify-between gap-4 border-b border-neutral-200 px-6 py-4">
            <div className="min-w-0 flex-1">
              {title && (
                <h2 id="modal-title" className="text-h3 text-neutral-900">
                  {title}
                </h2>
              )}
              {description && (
                <p id="modal-desc" className="mt-1 text-[13px] text-neutral-600">
                  {description}
                </p>
              )}
            </div>
            {!hideCloseButton && (
              <button
                type="button"
                aria-label="닫기"
                onClick={onClose}
                className="rounded p-1 text-neutral-500 hover:bg-neutral-100 focus-visible:outline-none focus-visible:shadow-focus"
              >
                <Icon as={X} size="md" />
              </button>
            )}
          </header>
        )}
        <div className="flex-1 overflow-auto px-6 py-4">{children}</div>
        {footer && (
          <footer className="flex justify-end gap-2 border-t border-neutral-200 px-6 py-3">
            {footer}
          </footer>
        )}
      </div>
    </dialog>
  );
}
