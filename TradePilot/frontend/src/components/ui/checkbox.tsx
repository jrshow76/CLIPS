'use client';

import { type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: ReactNode;
  className?: string;
}

export function Checkbox({ checked, onChange, disabled, label, className }: CheckboxProps) {
  return (
    <label
      className={cn('checkbox', checked && 'checkbox--checked', disabled && 'opacity-50', className)}
      onClick={() => !disabled && onChange(!checked)}
      onKeyDown={(e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          if (!disabled) onChange(!checked);
        }
      }}
      tabIndex={disabled ? -1 : 0}
      role="checkbox"
      aria-checked={checked}
      aria-disabled={disabled}
    >
      <span className="checkbox__box" />
      {label}
    </label>
  );
}
