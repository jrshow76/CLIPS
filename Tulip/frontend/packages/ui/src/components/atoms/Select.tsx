/**
 * Select — 단순 네이티브 select 래퍼 (DSN-03 §3.5 select variant).
 *
 * Combobox(검색가능)·multi-select는 Phase 1-D 이후 별도 컴포넌트로 분리.
 */
import { forwardRef, type ReactNode, type SelectHTMLAttributes } from 'react';

import { cn } from '../../lib/cn';

export interface SelectOption {
  value: string;
  label: ReactNode;
  disabled?: boolean;
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  options: SelectOption[];
  /** 첫 옵션 placeholder (값 = '') */
  placeholder?: string;
  size?: 'sm' | 'md' | 'lg';
  invalid?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { options, placeholder, className, size = 'md', invalid, ...rest },
  ref,
) {
  const sizeClass =
    size === 'sm' ? 'h-8 text-[13px] px-2' : size === 'lg' ? 'h-12 text-[16px] px-4' : 'h-10 text-[14px] px-3';
  return (
    <select
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        'rounded-md border bg-surface-card text-neutral-900',
        'focus-visible:outline-none focus-visible:shadow-focus',
        'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-neutral-100',
        invalid ? 'border-danger focus-visible:border-danger' : 'border-neutral-300 focus-visible:border-primary-500',
        sizeClass,
        className,
      )}
      {...rest}
    >
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {options.map((o) => (
        <option key={o.value} value={o.value} disabled={o.disabled}>
          {o.label}
        </option>
      ))}
    </select>
  );
});
