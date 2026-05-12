'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface DropdownItem {
  key: string;
  label: ReactNode;
  onSelect: () => void;
  danger?: boolean;
  disabled?: boolean;
}

export interface DropdownProps {
  trigger: ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
  className?: string;
}

/**
 * 간이 드롭다운. 메뉴/액션 묶음에 사용.
 * 접근성: aria-haspopup="menu", Esc로 닫기.
 */
export function Dropdown({ trigger, items, align = 'right', className }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className={cn('relative', className)}>
      <div onClick={() => setOpen((o) => !o)} aria-haspopup="menu" aria-expanded={open}>
        {trigger}
      </div>
      {open && (
        <div
          role="menu"
          className={cn(
            'border-border-2 bg-bg-2 shadow-2 absolute z-modal mt-1 min-w-[180px] rounded-md border p-1',
            align === 'right' ? 'right-0' : 'left-0',
          )}
        >
          {items.map((it) => (
            <button
              key={it.key}
              type="button"
              role="menuitem"
              disabled={it.disabled}
              className={cn(
                'hover:bg-bg-3 block w-full rounded-sm px-3 py-2 text-left text-13',
                it.danger && 'text-danger',
                it.disabled && 'opacity-50',
              )}
              onClick={() => {
                it.onSelect();
                setOpen(false);
              }}
            >
              {it.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
