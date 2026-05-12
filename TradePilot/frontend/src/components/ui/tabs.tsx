'use client';

import { type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface TabItem<T extends string> {
  value: T;
  label: ReactNode;
  count?: number;
  disabled?: boolean;
}

export interface TabsProps<T extends string> {
  value: T;
  items: TabItem<T>[];
  onChange: (next: T) => void;
  variant?: 'underline' | 'pill';
  className?: string;
}

export function Tabs<T extends string>({ value, items, onChange, variant = 'underline', className }: TabsProps<T>) {
  if (variant === 'pill') {
    return (
      <div className={cn('pill-tabs', className)} role="tablist">
        {items.map((it) => (
          <button
            key={it.value}
            type="button"
            role="tab"
            aria-selected={it.value === value}
            disabled={it.disabled}
            className={cn('pill-tabs__item', it.value === value && 'pill-tabs__item--active')}
            onClick={() => onChange(it.value)}
          >
            {it.label}
            {typeof it.count === 'number' && <span className="text-subtle ml-1">{it.count}</span>}
          </button>
        ))}
      </div>
    );
  }
  return (
    <div className={cn('tabs', className)} role="tablist">
      {items.map((it) => (
        <button
          key={it.value}
          type="button"
          role="tab"
          aria-selected={it.value === value}
          disabled={it.disabled}
          className={cn('tabs__item', it.value === value && 'tabs__item--active')}
          onClick={() => onChange(it.value)}
        >
          {it.label}
          {typeof it.count === 'number' && <span className="text-subtle ml-2">{it.count}</span>}
        </button>
      ))}
    </div>
  );
}
