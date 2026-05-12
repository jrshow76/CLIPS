'use client';

import { ChevronDown, ChevronUp } from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';

import { Pagination } from './pagination';
import { cn } from '@/lib/utils/cn';

export interface Column<T> {
  key: string;
  header: ReactNode;
  /** 셀 렌더러. 미지정 시 `row[key]` 출력. */
  cell?: (row: T, index: number) => ReactNode;
  /** 우측 정렬(숫자) */
  align?: 'left' | 'center' | 'right';
  /** 정렬 가능한 컬럼인 경우, 비교용 키 또는 함수 */
  sortAccessor?: keyof T | ((row: T) => string | number);
  width?: number | string;
  className?: string;
  headerClassName?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (row: T, index: number) => string;
  emptyMessage?: string;
  className?: string;
  /** 클라이언트 페이지네이션 사용 시 */
  pageSize?: number;
  compact?: boolean;
  /** 행 클릭 핸들러 */
  onRowClick?: (row: T) => void;
}

/**
 * DataTable: 정렬(클라이언트) + 페이지네이션(클라이언트) + 빈상태.
 * 서버 페이지네이션이 필요한 경우 BasicTable + 외부 Pagination 조합 사용 권장.
 */
export function DataTable<T>({
  columns,
  data,
  rowKey,
  emptyMessage = '데이터가 없습니다.',
  className,
  pageSize,
  compact,
  onRowClick,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.sortAccessor) return data;
    const acc = typeof col.sortAccessor === 'function' ? col.sortAccessor : (row: T) => row[col.sortAccessor as keyof T] as unknown as string | number;
    return [...data].sort((a, b) => {
      const av = acc(a);
      const bv = acc(b);
      if (av === bv) return 0;
      const dir = sortDir === 'asc' ? 1 : -1;
      return av > bv ? dir : -dir;
    });
  }, [data, sortKey, sortDir, columns]);

  const total = sorted.length;
  const pageCount = pageSize ? Math.max(1, Math.ceil(total / pageSize)) : 1;
  const view = pageSize ? sorted.slice((page - 1) * pageSize, page * pageSize) : sorted;

  function onSort(col: Column<T>) {
    if (!col.sortAccessor) return;
    if (sortKey === col.key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortKey(col.key);
      setSortDir('asc');
    }
  }

  return (
    <div className={cn('table-wrap', className)}>
      <div className="table-scroll">
        <table className={cn('table', compact && 'table--compact')}>
          <thead>
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  style={{ width: c.width, textAlign: c.align }}
                  className={cn(c.align === 'right' && 'num', c.align === 'center' && 'center', c.headerClassName)}
                >
                  {c.sortAccessor ? (
                    <button
                      type="button"
                      className="inline-flex items-center gap-1"
                      onClick={() => onSort(c)}
                    >
                      {c.header}
                      {sortKey === c.key &&
                        (sortDir === 'asc' ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronDown className="h-3 w-3" />
                        ))}
                    </button>
                  ) : (
                    c.header
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {view.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="text-subtle py-8 text-center">
                  {emptyMessage}
                </td>
              </tr>
            )}
            {view.map((row, i) => (
              <tr
                key={rowKey(row, i)}
                onClick={() => onRowClick?.(row)}
                className={onRowClick ? 'cursor-pointer' : undefined}
              >
                {columns.map((c) => (
                  <td
                    key={c.key}
                    style={{ textAlign: c.align }}
                    className={cn(c.align === 'right' && 'num', c.align === 'center' && 'center', c.className)}
                  >
                    {c.cell ? c.cell(row, i) : (row as Record<string, ReactNode>)[c.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pageSize && pageCount > 1 && (
        <Pagination page={page} pageCount={pageCount} total={total} onPageChange={setPage} />
      )}
    </div>
  );
}
