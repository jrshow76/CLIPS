'use client';

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatKSTDate } from '@/lib/utils/date';
import { formatCurrency } from '@/lib/utils/format';
import type { BacktestEquityPoint } from '@/types/backtest';

export interface BacktestEquityChartProps {
  data: BacktestEquityPoint[];
  height?: number;
}

export function BacktestEquityChart({ data, height = 360 }: BacktestEquityChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--chart-grid-1)" />
        <XAxis
          dataKey="ts"
          tickFormatter={(v) => formatKSTDate(v).slice(2, 10)}
          tick={{ fill: 'var(--color-text-3)', fontSize: 11 }}
        />
        <YAxis
          tickFormatter={(v: number) => `${Math.round(v / 10000)}만`}
          tick={{ fill: 'var(--color-text-3)', fontSize: 11 }}
          width={48}
        />
        <Tooltip
          contentStyle={{ background: 'var(--color-bg-2)', border: '1px solid var(--color-border-2)', fontSize: 12 }}
          formatter={(value: number, name: string) => [formatCurrency(value), name]}
          labelFormatter={(label) => formatKSTDate(label as number)}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="equity"
          name="전략 자산"
          stroke="var(--color-brand-500)"
          dot={false}
          strokeWidth={1.6}
        />
        <Line
          type="monotone"
          dataKey="benchmark"
          name="벤치마크"
          stroke="var(--color-text-3)"
          dot={false}
          strokeWidth={1}
          strokeDasharray="4 4"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
