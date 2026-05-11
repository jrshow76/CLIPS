'use client';

/**
 * Tabs — 단순 탭 컴포넌트 (DSN-03 §4.7 line variant).
 *
 * a11y: role=tablist/tab/tabpanel, 키보드 화살표/Home/End.
 *
 * Phase 1-C 단계는 lazy 렌더링·vertical 미지원. 추후 Radix Tabs로 교체 고려.
 */
import { useCallback, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';

import { cn } from '../../lib/cn';

export interface TabItem {
  id: string;
  label: ReactNode;
  /** 패널 내용 */
  content: ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  items: TabItem[];
  /** 제어 모드 활성 탭 ID */
  value?: string;
  defaultValue?: string;
  onChange?: (id: string) => void;
  className?: string;
}

export function Tabs({ items, value, defaultValue, onChange, className }: TabsProps) {
  const [internal, setInternal] = useState<string>(
    defaultValue ?? value ?? items[0]?.id ?? '',
  );
  const active = value ?? internal;
  const id = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const select = useCallback(
    (next: string) => {
      if (value === undefined) setInternal(next);
      onChange?.(next);
    },
    [onChange, value],
  );

  function handleKey(e: KeyboardEvent<HTMLDivElement>) {
    const idx = items.findIndex((t) => t.id === active);
    if (idx < 0) return;
    let nextIdx = idx;
    if (e.key === 'ArrowRight') nextIdx = (idx + 1) % items.length;
    else if (e.key === 'ArrowLeft') nextIdx = (idx - 1 + items.length) % items.length;
    else if (e.key === 'Home') nextIdx = 0;
    else if (e.key === 'End') nextIdx = items.length - 1;
    else return;
    e.preventDefault();
    const tab = items[nextIdx];
    if (!tab.disabled) {
      select(tab.id);
      refs.current[nextIdx]?.focus();
    }
  }

  return (
    <div className={cn('flex flex-col', className)}>
      <div role="tablist" onKeyDown={handleKey} className="flex gap-1 border-b border-neutral-200">
        {items.map((tab, i) => (
          <button
            key={tab.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            id={`${id}-tab-${tab.id}`}
            role="tab"
            type="button"
            aria-selected={tab.id === active}
            aria-controls={`${id}-panel-${tab.id}`}
            tabIndex={tab.id === active ? 0 : -1}
            disabled={tab.disabled}
            onClick={() => !tab.disabled && select(tab.id)}
            className={cn(
              'inline-flex h-10 items-center border-b-2 px-3 text-[13px] font-medium transition-colors',
              'focus-visible:outline-none focus-visible:shadow-focus',
              tab.disabled && 'cursor-not-allowed opacity-50',
              tab.id === active
                ? 'border-primary-500 text-primary-700'
                : 'border-transparent text-neutral-600 hover:text-neutral-900',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {items.map((tab) => (
        <div
          key={tab.id}
          id={`${id}-panel-${tab.id}`}
          role="tabpanel"
          aria-labelledby={`${id}-tab-${tab.id}`}
          hidden={tab.id !== active}
          className="pt-4"
        >
          {tab.id === active ? tab.content : null}
        </div>
      ))}
    </div>
  );
}
