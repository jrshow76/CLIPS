import { forwardRef, type TextareaHTMLAttributes } from 'react';

import { cn } from '@/lib/utils/cn';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { error, className, ...rest },
  ref,
) {
  return <textarea ref={ref} className={cn('textarea', error && 'textarea--has-error', className)} {...rest} />;
});
