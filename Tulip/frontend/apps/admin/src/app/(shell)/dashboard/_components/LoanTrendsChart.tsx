'use client';

import { useState } from 'react';
import {
  ChartContainer,
  LineChartBlock,
  type LineSeries,
} from '@tulip/ui';
import { useLoanTrendsQuery, type LoanTrendPoint } from '@tulip/api-client';

type LoanTrendRow = LoanTrendPoint & Record<string, unknown>;

const SERIES: LineSeries[] = [
  { dataKey: 'loans', label: '대출' },
  { dataKey: 'returns', label: '반납' },
  { dataKey: 'overdue', label: '연체' },
];

const RANGES: Array<{ value: 7 | 14 | 30; label: string }> = [
  { value: 7, label: '7일' },
  { value: 14, label: '14일' },
  { value: 30, label: '30일' },
];

function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function LoanTrendsChart({ libraryId }: { libraryId?: string }) {
  const [range, setRange] = useState<7 | 14 | 30>(14);
  const { data, isLoading, error, refetch } = useLoanTrendsQuery({ range, libraryId });

  return (
    <ChartContainer
      title="대출 추이"
      description={`최근 ${range}일 일자별 대출·반납·연체`}
      height={280}
      loading={isLoading}
      error={error ? { message: error.message, onRetry: () => refetch() } : null}
      empty={!isLoading && (data?.length ?? 0) === 0}
      actions={
        <div role="tablist" aria-label="기간 선택" className="flex gap-1">
          {RANGES.map((r) => (
            <button
              key={r.value}
              type="button"
              role="tab"
              aria-selected={range === r.value}
              onClick={() => setRange(r.value)}
              className={
                'rounded-md px-2.5 py-1 text-[12px] font-medium transition ' +
                (range === r.value
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-neutral-600 hover:bg-neutral-100')
              }
            >
              {r.label}
            </button>
          ))}
        </div>
      }
    >
      <LineChartBlock<LoanTrendRow>
        data={(data ?? []) as LoanTrendRow[]}
        xKey="date"
        series={SERIES}
        smooth
        ariaLabel="일자별 대출·반납·연체 추이"
        xTickFormatter={formatDate}
      />
    </ChartContainer>
  );
}
