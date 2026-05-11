'use client';

/**
 * FilterBar — 리스트 페이지 상단 검색·필터 컨테이너.
 *
 * - 좌측: 키워드 SearchBar (compact)
 * - 우측: 자유 슬롯(드롭다운·날짜 필터 등)
 * - 하단: 활성 필터 칩 표시 슬롯
 *
 * 사용처: 회원/도서관/대출 목록 등 ListPage 공통.
 */
import { Search } from 'lucide-react';
import { useState, type FormEvent, type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Button } from '../atoms/Button';
import { Icon } from '../atoms/Icon';

export interface FilterBarProps {
  /** 키워드 초기값 */
  defaultKeyword?: string;
  /** 키워드 placeholder */
  placeholder?: string;
  /** 검색 제출 — Enter 또는 검색 버튼 */
  onSearch?: (keyword: string) => void;
  /** 키워드 입력 옆 슬롯 (드롭다운·셀렉트 등) */
  filters?: ReactNode;
  /** 우측 액션 슬롯 (등록 버튼 등) */
  actions?: ReactNode;
  /** 활성 필터 칩 슬롯 */
  chips?: ReactNode;
  /** "초기화" 버튼 표시 — 클릭 시 onReset 호출 */
  onReset?: () => void;
  className?: string;
}

export function FilterBar({
  defaultKeyword = '',
  placeholder = '검색어 입력',
  onSearch,
  filters,
  actions,
  chips,
  onReset,
  className,
}: FilterBarProps) {
  const [keyword, setKeyword] = useState(defaultKeyword);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    onSearch?.(keyword.trim());
  }

  return (
    <div
      className={cn(
        'flex flex-col gap-3 rounded-lg border border-neutral-200 bg-surface-card p-3',
        className,
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <form role="search" onSubmit={handleSubmit} className="relative flex-1 min-w-60">
          <span
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500"
          >
            <Icon as={Search} size="sm" />
          </span>
          <input
            type="search"
            name="q"
            aria-label="검색어"
            placeholder={placeholder}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            className={cn(
              'h-10 w-full rounded-md border border-neutral-300 bg-surface-card pl-9 pr-3 text-[13px]',
              'placeholder:text-neutral-500 focus-visible:outline-none focus-visible:shadow-focus focus-visible:border-primary-500',
            )}
          />
        </form>
        {filters && <div className="flex flex-wrap items-center gap-2">{filters}</div>}
        <div className="ml-auto flex items-center gap-2">
          {onReset && (
            <Button variant="ghost" size="sm" onClick={onReset}>
              초기화
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={() => onSearch?.(keyword.trim())}>
            검색
          </Button>
          {actions}
        </div>
      </div>
      {chips && <div className="flex flex-wrap items-center gap-2">{chips}</div>}
    </div>
  );
}
