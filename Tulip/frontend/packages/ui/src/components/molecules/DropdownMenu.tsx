'use client';

/**
 * DropdownMenu — 단순 드롭다운 메뉴 (헤더 사용자 메뉴 등).
 *
 * - 외부 클릭 / ESC 닫기, 키보드 ↑↓ 네비.
 * - Phase 1-B에서 Radix Menu로 교체 검토.
 */
import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from 'react';

import { cn } from '../../lib/cn';

export interface DropdownMenuItem {
  id: string;
  label: ReactNode;
  /** 그룹 구분 헤더 */
  isHeader?: boolean;
  /** 비활성화 */
  disabled?: boolean;
  /** 우측 단축키 표시 */
  shortcut?: string;
  /** 좌측 아이콘 */
  icon?: ReactNode;
  onSelect?: () => void;
  /** 위험 강조 (삭제 등) */
  danger?: boolean;
}

export interface DropdownMenuProps {
  /** 트리거 (버튼 등) — render prop */
  trigger: (props: { onClick: () => void; 'aria-expanded': boolean; 'aria-haspopup': 'menu' }) => ReactNode;
  items: DropdownMenuItem[];
  align?: 'start' | 'end';
  className?: string;
}

export function DropdownMenu({ trigger, items, align = 'end', className }: DropdownMenuProps) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) close();
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open, close]);

  return (
    <div ref={wrapperRef} className={cn('relative inline-block', className)}>
      {trigger({
        onClick: () => setOpen((v) => !v),
        'aria-expanded': open,
        'aria-haspopup': 'menu',
      })}
      {open && (
        <ul
          id={menuId}
          role="menu"
          className={cn(
            'absolute z-dropdown mt-1 min-w-44 rounded-md border border-neutral-200 bg-surface-raised py-1 shadow-md',
            align === 'end' ? 'right-0' : 'left-0',
          )}
        >
          {items.map((item) =>
            item.isHeader ? (
              <li
                key={item.id}
                role="presentation"
                className="px-3 py-1 text-overline text-neutral-500"
              >
                {item.label}
              </li>
            ) : (
              <li key={item.id} role="none">
                <button
                  type="button"
                  role="menuitem"
                  disabled={item.disabled}
                  onClick={() => {
                    item.onSelect?.();
                    close();
                  }}
                  className={cn(
                    'flex w-full items-center gap-2 px-3 py-2 text-left text-[13px]',
                    'hover:bg-neutral-100 focus-visible:bg-neutral-100 focus-visible:outline-none',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    item.danger ? 'text-danger' : 'text-neutral-800',
                  )}
                >
                  {item.icon && <span className="shrink-0">{item.icon}</span>}
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.shortcut && (
                    <span className="text-[11px] text-neutral-500">{item.shortcut}</span>
                  )}
                </button>
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  );
}
