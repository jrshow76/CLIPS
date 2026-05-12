'use client';

import { useState, type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  placement?: 'top' | 'bottom';
  className?: string;
}

/** 간이 CSS 툴팁. 키보드 포커스 시에도 노출. */
export function Tooltip({ content, children, placement = 'top', className }: TooltipProps) {
  const [open, setOpen] = useState(false);
  return (
    <span
      className={cn('relative inline-flex', className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && (
        <span
          role="tooltip"
          className={cn(
            'border-border-2 bg-bg-2 text-fg-1 shadow-2 absolute z-modal whitespace-nowrap rounded-md border px-2 py-1 text-12',
            placement === 'top' ? 'bottom-full mb-1' : 'top-full mt-1',
            'left-1/2 -translate-x-1/2',
          )}
        >
          {content}
        </span>
      )}
    </span>
  );
}
