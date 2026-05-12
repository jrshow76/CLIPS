'use client';

import { X } from 'lucide-react';
import { useEffect, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { Button } from './button';
import { cn } from '@/lib/utils/cn';

export type ModalSize = 'sm' | 'md' | 'lg' | 'xl';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  size?: ModalSize;
  /** 위험 액션(LIVE 전환, 청산 등)용. 상단 빨간 라인 */
  danger?: boolean;
  closeOnBackdrop?: boolean;
  hideClose?: boolean;
  footer?: ReactNode;
  children: ReactNode;
}

/**
 * Designer .modal-mask + .modal BEM 매핑.
 * - Portal로 body에 마운트, Esc 키로 닫기, 포커스 트랩(간이).
 * - danger 변형은 LiveModeModal/주문 확인에 사용.
 */
export function Modal({
  open,
  onClose,
  title,
  size = 'md',
  danger,
  closeOnBackdrop = true,
  hideClose,
  footer,
  children,
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    // 첫 포커스
    dialogRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open || typeof document === 'undefined') return null;

  const sizeClass = size === 'lg' ? 'modal--lg' : size === 'xl' ? 'modal--xl' : size === 'sm' ? '' : '';

  return createPortal(
    <div
      className="modal-mask"
      onMouseDown={(e) => {
        if (closeOnBackdrop && e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : undefined}
        tabIndex={-1}
        className={cn('modal', sizeClass, danger && 'modal--danger')}
      >
        {(title || !hideClose) && (
          <header className="modal__header">
            <h3 className="modal__title">{title}</h3>
            {!hideClose && (
              <Button variant="ghost" size="icon" onClick={onClose} aria-label="닫기">
                <X className="h-4 w-4" />
              </Button>
            )}
          </header>
        )}
        <div className="modal__body">{children}</div>
        {footer && <footer className="modal__footer">{footer}</footer>}
      </div>
    </div>,
    document.body,
  );
}
