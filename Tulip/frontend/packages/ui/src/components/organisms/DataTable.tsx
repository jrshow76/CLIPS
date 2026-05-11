/**
 * DataTable — 사서 시스템 핵심 테이블 (DSN-03 §5.1)
 *
 * 본 단계는 기본 구조만 제공:
 *   - 컬럼 정의(`Column<T>`)
 *   - 정렬 토글 (외부 제어, aria-sort)
 *   - 행 선택 (체크박스)
 *   - density 변형 (compact / comfortable)
 *   - 로딩·빈 상태
 * 가상스크롤·인라인 편집 등은 Phase 1-B에서 확장.
 */
import { type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Spinner } from '../atoms/Spinner';

export type SortDirection = 'asc' | 'desc' | null;

export interface Column<T> {
  id: string;
  header: ReactNode;
  /** 셀 렌더링 */
  cell: (row: T) => ReactNode;
  /** 정렬 가능 */
  sortable?: boolean;
  /** 우측 정렬 (숫자) */
  align?: 'left' | 'right' | 'center';
  /** 폭 (px 또는 css) */
  width?: number | string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  /** 고유 키 추출자 */
  rowKey: (row: T) => string;
  /** 로딩 상태 */
  loading?: boolean;
  /** 정렬 상태 */
  sort?: { columnId: string; direction: Exclude<SortDirection, null> };
  /** 정렬 변경 핸들러 */
  onSortChange?: (sort: { columnId: string; direction: Exclude<SortDirection, null> } | null) => void;
  /** 선택된 행 ID 집합 */
  selectedIds?: Set<string>;
  /** 선택 변경 핸들러 */
  onSelectionChange?: (ids: Set<string>) => void;
  /** 행 클릭 */
  onRowClick?: (row: T) => void;
  /** 빈 상태 표시 */
  empty?: ReactNode;
  /** 캡션 (a11y) */
  caption?: ReactNode;
  /** 밀도 */
  density?: 'compact' | 'comfortable';
  className?: string;
}

export function DataTable<T>({
  columns,
  data,
  rowKey,
  loading,
  sort,
  onSortChange,
  selectedIds,
  onSelectionChange,
  onRowClick,
  empty,
  caption,
  density = 'comfortable',
  className,
}: DataTableProps<T>) {
  const selectable = !!onSelectionChange;
  const cellPad = density === 'compact' ? 'px-3 py-2' : 'px-3 py-3';

  function toggleSort(col: Column<T>) {
    if (!col.sortable || !onSortChange) return;
    if (!sort || sort.columnId !== col.id) {
      onSortChange({ columnId: col.id, direction: 'asc' });
    } else if (sort.direction === 'asc') {
      onSortChange({ columnId: col.id, direction: 'desc' });
    } else {
      onSortChange(null);
    }
  }

  function toggleRow(id: string) {
    if (!onSelectionChange) return;
    const next = new Set(selectedIds ?? []);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectionChange(next);
  }

  function toggleAll() {
    if (!onSelectionChange) return;
    if (selectedIds && selectedIds.size === data.length) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(new Set(data.map(rowKey)));
    }
  }

  return (
    <div className={cn('overflow-x-auto rounded-lg border border-neutral-200', className)}>
      <table className="w-full border-collapse text-left text-[13px] tabular-nums">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead className="bg-neutral-50 text-overline text-neutral-600">
          <tr>
            {selectable && (
              <th scope="col" className={cn('w-10', cellPad)}>
                <input
                  type="checkbox"
                  aria-label="전체 선택"
                  checked={data.length > 0 && (selectedIds?.size ?? 0) === data.length}
                  onChange={toggleAll}
                  className="rounded border-neutral-300 text-primary-500 focus-visible:shadow-focus"
                />
              </th>
            )}
            {columns.map((col) => {
              const active = sort?.columnId === col.id;
              const ariaSort: 'ascending' | 'descending' | 'none' = active
                ? sort!.direction === 'asc'
                  ? 'ascending'
                  : 'descending'
                : 'none';
              return (
                <th
                  key={col.id}
                  scope="col"
                  style={{ width: col.width }}
                  aria-sort={col.sortable ? ariaSort : undefined}
                  className={cn(
                    cellPad,
                    'border-b border-neutral-200 font-semibold uppercase tracking-wider',
                    col.align === 'right' && 'text-right',
                    col.align === 'center' && 'text-center',
                  )}
                >
                  {col.sortable ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(col)}
                      className="inline-flex items-center gap-1 hover:text-neutral-900 focus-visible:outline-none focus-visible:shadow-focus rounded"
                    >
                      {col.header}
                      <span aria-hidden="true" className="text-[10px]">
                        {active ? (sort!.direction === 'asc' ? '↑' : '↓') : '↕'}
                      </span>
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {loading && (
            <tr>
              <td
                colSpan={columns.length + (selectable ? 1 : 0)}
                className="px-3 py-8 text-center text-neutral-500"
              >
                <Spinner size="md" /> <span className="ml-2 align-middle">로딩 중…</span>
              </td>
            </tr>
          )}
          {!loading && data.length === 0 && (
            <tr>
              <td
                colSpan={columns.length + (selectable ? 1 : 0)}
                className="px-3 py-8 text-center text-neutral-500"
              >
                {empty ?? '표시할 데이터가 없습니다.'}
              </td>
            </tr>
          )}
          {!loading &&
            data.map((row) => {
              const id = rowKey(row);
              const selected = selectedIds?.has(id) ?? false;
              return (
                <tr
                  key={id}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={cn(
                    'border-b border-neutral-100 transition-colors',
                    onRowClick && 'cursor-pointer',
                    selected ? 'bg-primary-50' : 'hover:bg-neutral-50',
                  )}
                >
                  {selectable && (
                    <td className={cellPad}>
                      <input
                        type="checkbox"
                        aria-label={`행 ${id} 선택`}
                        checked={selected}
                        onChange={() => toggleRow(id)}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded border-neutral-300 text-primary-500 focus-visible:shadow-focus"
                      />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td
                      key={col.id}
                      className={cn(
                        cellPad,
                        'text-neutral-800',
                        col.align === 'right' && 'text-right',
                        col.align === 'center' && 'text-center',
                      )}
                    >
                      {col.cell(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
        </tbody>
      </table>
    </div>
  );
}
