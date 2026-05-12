'use client';

import { cn } from '@/lib/utils/cn';

export interface SwitchProps {
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
  ariaLabel?: string;
  className?: string;
}

export function Switch({ checked, onChange, disabled, ariaLabel, className }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      aria-disabled={disabled}
      disabled={disabled}
      className={cn('switch', checked && 'switch--on', className)}
      onClick={() => !disabled && onChange(!checked)}
    />
  );
}
