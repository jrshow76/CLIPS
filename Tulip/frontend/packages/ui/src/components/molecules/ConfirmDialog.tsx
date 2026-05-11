'use client';

/**
 * ConfirmDialog — 위험 작업 확인용 모달.
 *
 * 사용:
 *   <ConfirmDialog
 *     open={open}
 *     title="회원을 삭제하시겠습니까?"
 *     description="삭제 후에는 복구할 수 없습니다."
 *     confirmText="삭제"
 *     tone="danger"
 *     onConfirm={...}
 *     onCancel={...}
 *   />
 */
import { type ReactNode } from 'react';

import { Button } from '../atoms/Button';

import { Modal } from './Modal';

export interface ConfirmDialogProps {
  open: boolean;
  title: ReactNode;
  description?: ReactNode;
  confirmText?: string;
  cancelText?: string;
  /** 위험 액션 강조 (danger 버튼) */
  tone?: 'primary' | 'danger';
  /** 로딩 중 비활성화 */
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmText = '확인',
  cancelText = '취소',
  tone = 'primary',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      description={description}
      size="sm"
      closeOnBackdrop={!loading}
      closeOnEsc={!loading}
      hideCloseButton
      footer={
        <>
          <Button variant="secondary" size="sm" onClick={onCancel} disabled={loading}>
            {cancelText}
          </Button>
          <Button
            variant={tone === 'danger' ? 'danger' : 'primary'}
            size="sm"
            onClick={onConfirm}
            loading={loading}
          >
            {confirmText}
          </Button>
        </>
      }
    >
      {/* description은 Modal header에서 노출되므로 본문은 비워둠 (필요시 children 확장) */}
      <div className="sr-only">확인 다이얼로그</div>
    </Modal>
  );
}
