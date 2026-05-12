import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  leftIcon?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { error, leftIcon, className, ...rest },
  ref,
) {
  const inputEl = (
    <input
      ref={ref}
      className={cn('input', leftIcon && 'input--prefix-pad', error && 'input--has-error', className)}
      {...rest}
    />
  );
  if (!leftIcon) return inputEl;
  return (
    <div className="input-group">
      <span className="input-group__icon" aria-hidden="true">
        {leftIcon}
      </span>
      {inputEl}
    </div>
  );
});

/* ---------- Field (Label + Hint + Error 조합) ---------- */
export interface FieldProps {
  label?: string;
  hint?: string;
  error?: string;
  htmlFor?: string;
  required?: boolean;
  className?: string;
  children: ReactNode;
}

export function Field({ label, hint, error, htmlFor, required, className, children }: FieldProps) {
  return (
    <div className={cn('field', className)}>
      {label && (
        <label className="field__label" htmlFor={htmlFor}>
          {label}
          {required && <span className="text-up ml-1">*</span>}
        </label>
      )}
      {children}
      {hint && !error && <span className="field__hint">{hint}</span>}
      {error && <span className="field__error">{error}</span>}
    </div>
  );
}
