/**
 * Label — 폼 라벨.
 * a11y: <label for={id}>; required=true 시 시각적 *와 aria-required.
 */
import { forwardRef, type LabelHTMLAttributes } from 'react';

import { cn } from '../../lib/cn';

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
  /** 시각적 강조 (h4 스타일) */
  emphasis?: boolean;
}

export const Label = forwardRef<HTMLLabelElement, LabelProps>(function Label(
  { className, required, emphasis, children, ...rest },
  ref,
) {
  return (
    <label
      ref={ref}
      className={cn(
        'inline-flex items-center gap-1 text-neutral-700',
        emphasis ? 'text-[16px] font-semibold' : 'text-[13px] font-medium',
        rest['aria-disabled'] && 'opacity-50',
        className,
      )}
      {...rest}
    >
      {children}
      {required && (
        <span aria-hidden="true" className="text-danger">
          *
        </span>
      )}
    </label>
  );
});
