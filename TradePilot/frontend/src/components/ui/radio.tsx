'use client';

import { type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface RadioOption<T extends string> {
  value: T;
  label: ReactNode;
  disabled?: boolean;
}

export interface RadioGroupProps<T extends string> {
  name: string;
  value: T;
  options: RadioOption<T>[];
  onChange: (next: T) => void;
  className?: string;
}

/** 시각적으로는 checkbox 스타일을 재활용 (원형 마커 대체 가능) */
export function RadioGroup<T extends string>({ name, value, options, onChange, className }: RadioGroupProps<T>) {
  return (
    <div role="radiogroup" className={cn('flex flex-wrap gap-3', className)}>
      {options.map((opt) => (
        <label
          key={opt.value}
          className={cn('checkbox', value === opt.value && 'checkbox--checked', opt.disabled && 'opacity-50')}
        >
          <input
            type="radio"
            name={name}
            value={opt.value}
            checked={value === opt.value}
            onChange={() => onChange(opt.value)}
            disabled={opt.disabled}
            className="sr-only"
          />
          <span className="checkbox__box" />
          {opt.label}
        </label>
      ))}
    </div>
  );
}
