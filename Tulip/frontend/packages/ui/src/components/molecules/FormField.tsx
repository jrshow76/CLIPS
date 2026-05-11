'use client';

/**
 * FormField — Label + Control + HelpText + Error 묶음.
 *
 * a11y:
 * - Label은 htmlFor로 id 자동 연결
 * - Error 존재 시 aria-describedby로 control과 연결
 */
import { useId, type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Label } from '../atoms/Label';

export interface FormFieldProps {
  /** 라벨 텍스트 */
  label?: ReactNode;
  /** 필수 항목 */
  required?: boolean;
  /** 입력 도움말 */
  helpText?: ReactNode;
  /** 에러 메시지 */
  error?: ReactNode;
  /** 자식 컨트롤 (id·aria 자동 주입) */
  children: (props: { id: string; 'aria-describedby'?: string; 'aria-invalid'?: boolean }) => ReactNode;
  className?: string;
  /** 수평 정렬 (inline) */
  inline?: boolean;
}

export function FormField({
  label,
  required,
  helpText,
  error,
  children,
  className,
  inline,
}: FormFieldProps) {
  const id = useId();
  const helpId = helpText ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [helpId, errorId].filter(Boolean).join(' ') || undefined;

  return (
    <div
      className={cn(
        'flex gap-2',
        inline ? 'flex-row items-center' : 'flex-col',
        className,
      )}
    >
      {label && (
        <Label htmlFor={id} required={required} className={inline ? 'min-w-24' : ''}>
          {label}
        </Label>
      )}
      <div className="flex-1">
        {children({
          id,
          'aria-describedby': describedBy,
          'aria-invalid': error ? true : undefined,
        })}
        {helpText && !error && (
          <p id={helpId} className="mt-1 text-[12px] text-neutral-500">
            {helpText}
          </p>
        )}
        {error && (
          <p id={errorId} role="alert" className="mt-1 text-[12px] text-danger">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
