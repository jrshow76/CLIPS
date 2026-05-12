'use client';

import { Search } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { Input } from '@/components/ui/input';
import { useStockSearch } from '@/lib/api/queries/stock-search';
import { cn } from '@/lib/utils/cn';
import type { Stock } from '@/types/stock';

export interface StockSearchInputProps {
  value?: Stock | null;
  onSelect: (stock: Stock) => void;
  placeholder?: string;
  autoFocus?: boolean;
  className?: string;
  /** 입력 박스 disabled 처리 */
  disabled?: boolean;
}

/**
 * 종목 검색 자동완성 (200ms 디바운스).
 * - 키보드: ↑/↓ 이동, Enter 선택, Esc 닫기.
 * - Mock 모드에서는 mockStockMaster 20종목 prefix 매칭.
 */
export function StockSearchInput({
  value,
  onSelect,
  placeholder = '종목명 또는 코드 검색',
  autoFocus,
  className,
  disabled,
}: StockSearchInputProps) {
  const [text, setText] = useState(value ? `${value.name} (${value.code})` : '');
  const [debounced, setDebounced] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(text), 200);
    return () => clearTimeout(t);
  }, [text]);

  const { data, isFetching } = useStockSearch(debounced);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  function pick(stock: Stock) {
    onSelect(stock);
    setText(`${stock.name} (${stock.code})`);
    setOpen(false);
  }

  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || !data?.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, data.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const picked = data[activeIdx];
      if (picked) pick(picked);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }

  return (
    <div ref={wrapRef} className={cn('relative', className)} style={{ position: 'relative' }}>
      <Input
        leftIcon={<Search className="h-4 w-4" />}
        placeholder={placeholder}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          setActiveIdx(0);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKey}
        autoFocus={autoFocus}
        disabled={disabled}
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={open}
      />
      {open && debounced.length >= 1 && (
        <div
          role="listbox"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            right: 0,
            background: 'var(--color-bg-2)',
            border: '1px solid var(--color-border-2)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-lg)',
            zIndex: 30,
            maxHeight: 280,
            overflowY: 'auto',
          }}
        >
          {isFetching && <p className="text-subtle p-3 text-sm">검색 중...</p>}
          {!isFetching && data && data.length === 0 && (
            <p className="text-subtle p-3 text-sm">검색 결과가 없습니다.</p>
          )}
          {data?.map((s, i) => (
            <button
              key={s.code}
              type="button"
              role="option"
              aria-selected={i === activeIdx}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick(s)}
              className={cn(
                'row items-center justify-between w-full px-3 py-2 text-left',
                i === activeIdx && 'bg-bg-3',
              )}
              style={{
                background: i === activeIdx ? 'var(--color-bg-3)' : undefined,
                width: '100%',
              }}
              onMouseEnter={() => setActiveIdx(i)}
            >
              <div>
                <span className="fw-semibold text-strong">{s.name}</span>
                <span className="text-xs text-subtle ml-2">{s.code}</span>
              </div>
              <span className="text-xs text-subtle">{s.market}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
