'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';

import { cn } from '@/lib/utils/cn';

export interface PaginationProps {
  page: number;
  pageCount: number;
  total?: number | null;
  onPageChange: (page: number) => void;
  className?: string;
  windowSize?: number;
}

export function Pagination({
  page,
  pageCount,
  total,
  onPageChange,
  className,
  windowSize = 5,
}: PaginationProps) {
  const half = Math.floor(windowSize / 2);
  const start = Math.max(1, Math.min(page - half, pageCount - windowSize + 1));
  const end = Math.min(pageCount, start + windowSize - 1);
  const pages = Array.from({ length: end - start + 1 }, (_, i) => start + i);

  return (
    <nav className={cn('pager', className)} aria-label="페이지네이션">
      <div>
        {typeof total === 'number' ? `총 ${total.toLocaleString('ko-KR')}건 · ` : ''}
        {page} / {pageCount}페이지
      </div>
      <div className="pager__pages">
        <button
          type="button"
          className="pager__page"
          aria-label="이전 페이지"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        {pages.map((p) => (
          <button
            key={p}
            type="button"
            className={cn('pager__page', p === page && 'pager__page--active')}
            onClick={() => onPageChange(p)}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        ))}
        <button
          type="button"
          className="pager__page"
          aria-label="다음 페이지"
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </nav>
  );
}
