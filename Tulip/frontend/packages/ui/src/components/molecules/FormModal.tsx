'use client';

/**
 * FormModal — Modal + Form 통합 래퍼.
 *
 * - children 영역은 폼 컨텐츠
 * - 푸터에 자동으로 취소/저장 버튼 렌더 (커스텀 가능)
 * - submit 시 onSubmit 호출 (preventDefault 처리됨)
 *
 * 사용:
 *   <FormModal open={open} title="회원 등록" onClose={...} onSubmit={handleSubmit}>
 *     ...폼 필드...
 *   </FormModal>
 */
import { type FormEvent, type ReactNode } from 'react';

import { Button } from '../atoms/Button';

import { Modal, type ModalSize } from './Modal';

export interface FormModalProps {
  open: boolean;
  title: ReactNode;
  description?: ReactNode;
  size?: ModalSize;
  /** 저장 버튼 라벨 */
  submitText?: string;
  /** 취소 버튼 라벨 */
  cancelText?: string;
  /** 제출 처리중 (저장 버튼 loading + 모달 닫기 방지) */
  submitting?: boolean;
  /** 추가 비활성화 (검증 실패 등) */
  disabled?: boolean;
  /** form id — 외부 버튼이 form 제출을 트리거할 때 사용 */
  formId?: string;
  /** 푸터 좌측 슬롯 (보조 액션) */
  footerLeft?: ReactNode;
  /** 자체 푸터 사용 시 기본 푸터 숨김 */
  hideDefaultFooter?: boolean;
  onClose: () => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}

export function FormModal({
  open,
  title,
  description,
  size = 'lg',
  submitText = '저장',
  cancelText = '취소',
  submitting = false,
  disabled = false,
  formId,
  footerLeft,
  hideDefaultFooter = false,
  onClose,
  onSubmit,
  children,
}: FormModalProps) {
  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    onSubmit(e);
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      size={size}
      closeOnBackdrop={!submitting}
      closeOnEsc={!submitting}
      footer={
        hideDefaultFooter ? undefined : (
          <>
            {footerLeft && <div className="mr-auto">{footerLeft}</div>}
            <Button
              variant="secondary"
              size="sm"
              onClick={onClose}
              disabled={submitting}
            >
              {cancelText}
            </Button>
            <Button
              type="submit"
              form={formId}
              variant="primary"
              size="sm"
              loading={submitting}
              disabled={disabled}
            >
              {submitText}
            </Button>
          </>
        )
      }
    >
      <form id={formId} onSubmit={handleSubmit} className="flex flex-col gap-4">
        {children}
      </form>
    </Modal>
  );
}
