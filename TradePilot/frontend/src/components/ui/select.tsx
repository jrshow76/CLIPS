import { forwardRef, type SelectHTMLAttributes } from 'react';

import { cn } from '@/lib/utils/cn';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { error, className, children, ...rest },
  ref,
) {
  return (
    <select ref={ref} className={cn('select', error && 'select--has-error', className)} {...rest}>
      {children}
    </select>
  );
});
