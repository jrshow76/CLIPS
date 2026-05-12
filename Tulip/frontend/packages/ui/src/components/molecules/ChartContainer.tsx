/**
 * ChartContainer — 차트 상위 컨테이너 (제목·범례·상태 통합)
 *
 * 표준 상태:
 *   - loading: Skeleton + spinner
 *   - error: 인라인 에러 메시지 + 재시도
 *   - empty: EmptyState 단순 텍스트
 *   - default: children (Recharts ResponsiveContainer 권장)
 */
import { AlertTriangle, RefreshCcw } from 'lucide-react';
import { type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Icon } from '../atoms/Icon';
import { Skeleton } from '../atoms/Skeleton';

export interface ChartContainerProps {
  title: ReactNode;
  description?: ReactNode;
  /** 우측 액션 (필터·범위 선택 등) */
  actions?: ReactNode;
  /** 하단 범례 슬롯 */
  legend?: ReactNode;
  /** 차트 높이 (px) — 기본 240 */
  height?: number;
  loading?: boolean;
  error?: { message: string; onRetry?: () => void } | null;
  empty?: boolean;
  emptyMessage?: ReactNode;
  className?: string;
  children?: ReactNode;
}

export function ChartContainer({
  title,
  description,
  actions,
  legend,
  height = 240,
  loading = false,
  error = null,
  empty = false,
  emptyMessage = '표시할 데이터가 없습니다.',
  className,
  children,
}: ChartContainerProps) {
  return (
    <section
      className={cn(
        'flex flex-col rounded-lg border border-neutral-200 bg-surface-card p-4 shadow-sm',
        className,
      )}
      aria-busy={loading || undefined}
    >
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-[15px] font-semibold text-neutral-900">{title}</h3>
          {description && (
            <p className="mt-0.5 text-[12px] text-neutral-500">{description}</p>
          )}
        </div>
        {actions && <div className="shrink-0">{actions}</div>}
      </header>
      <div className="mt-3" style={{ minHeight: height }}>
        {loading ? (
          <div className="flex flex-col gap-2" style={{ height }}>
            <Skeleton className="h-full w-full" />
          </div>
        ) : error ? (
          <div
            role="alert"
            className="flex h-full flex-col items-center justify-center gap-2 text-center text-[13px] text-danger"
            style={{ height }}
          >
            <Icon as={AlertTriangle} size="md" />
            <span>{error.message}</span>
            {error.onRetry && (
              <button
                type="button"
                onClick={error.onRetry}
                className="mt-1 inline-flex items-center gap-1 rounded-md border border-neutral-300 px-2 py-1 text-[12px] text-neutral-700 hover:bg-neutral-100"
              >
                <Icon as={RefreshCcw} size="xs" />
                재시도
              </button>
            )}
          </div>
        ) : empty ? (
          <div
            className="flex h-full items-center justify-center text-[13px] text-neutral-500"
            style={{ height }}
          >
            {emptyMessage}
          </div>
        ) : (
          <div style={{ height }} className="w-full">
            {children}
          </div>
        )}
      </div>
      {legend && !loading && !error && !empty && (
        <footer className="mt-2 flex flex-wrap items-center gap-3 text-[12px] text-neutral-600">
          {legend}
        </footer>
      )}
    </section>
  );
}
