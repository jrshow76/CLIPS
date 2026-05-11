'use client';

/**
 * Pagination — 페이지 번호 네비게이션 (DSN-03 §4.3)
 *
 * a11y: <nav aria-label="페이지">, 현재 페이지 aria-current=page.
 */
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useMemo } from 'react';

import { cn } from '../../lib/cn';
import { Icon } from '../atoms/Icon';

export interface PaginationProps {
  /** 현재 페이지 (1-base) */
  current: number;
  /** 총 페이지 수 */
  totalPages: number;
  /** 변경 핸들러 */
  onChange: (page: number) => void;
  /** 좌우에 표시할 페이지 수 */
  siblingCount?: number;
  className?: string;
}

function range(start: number, end: number): number[] {
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
}

export function Pagination({
  current,
  totalPages,
  onChange,
  siblingCount = 1,
  className,
}: PaginationProps) {
  const pages = useMemo<(number | 'dots')[]>(() => {
    if (totalPages <= 7) return range(1, totalPages);

    const left = Math.max(current - siblingCount, 2);
    const right = Math.min(current + siblingCount, totalPages - 1);
    const showLeftDots = left > 2;
    const showRightDots = right < totalPages - 1;

    const result: (number | 'dots')[] = [1];
    if (showLeftDots) result.push('dots');
    result.push(...range(left, right));
    if (showRightDots) result.push('dots');
    result.push(totalPages);
    return result;
  }, [current, totalPages, siblingCount]);

  const canPrev = current > 1;
  const canNext = current < totalPages;

  return (
    <nav aria-label="페이지" className={cn('flex items-center gap-1', className)}>
      <button
        type="button"
        aria-label="이전 페이지"
        disabled={!canPrev}
        onClick={() => canPrev && onChange(current - 1)}
        className={cn(
          'inline-flex h-8 w-8 items-center justify-center rounded-md text-neutral-700',
          'hover:bg-neutral-100 disabled:opacity-40 disabled:cursor-not-allowed',
          'focus-visible:outline-none focus-visible:shadow-focus',
        )}
      >
        <Icon as={ChevronLeft} size="sm" />
      </button>
      {pages.map((p, i) =>
        p === 'dots' ? (
          <span
            key={`dots-${i}`}
            aria-hidden="true"
            className="px-2 text-neutral-500 select-none"
          >
            …
          </span>
        ) : (
          <button
            key={p}
            type="button"
            aria-current={p === current ? 'page' : undefined}
            aria-label={`페이지 ${p}`}
            onClick={() => onChange(p)}
            className={cn(
              'inline-flex h-8 min-w-8 items-center justify-center rounded-md px-2 text-[13px]',
              'transition-colors focus-visible:outline-none focus-visible:shadow-focus',
              p === current
                ? 'bg-primary-500 text-white font-semibold'
                : 'text-neutral-700 hover:bg-neutral-100',
            )}
          >
            {p}
          </button>
        ),
      )}
      <button
        type="button"
        aria-label="다음 페이지"
        disabled={!canNext}
        onClick={() => canNext && onChange(current + 1)}
        className={cn(
          'inline-flex h-8 w-8 items-center justify-center rounded-md text-neutral-700',
          'hover:bg-neutral-100 disabled:opacity-40 disabled:cursor-not-allowed',
          'focus-visible:outline-none focus-visible:shadow-focus',
        )}
      >
        <Icon as={ChevronRight} size="sm" />
      </button>
    </nav>
  );
}
