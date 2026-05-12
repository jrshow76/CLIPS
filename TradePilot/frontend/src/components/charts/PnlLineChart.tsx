'use client';

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatKSTDate } from '@/lib/utils/date';
import { formatCurrency } from '@/lib/utils/format';

export interface PnlLineChartProps {
  data: { ts: number; equity: number }[];
  height?: number;
}

export function PnlLineChart({ data, height = 280 }: PnlLineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--color-brand-500)" stopOpacity={0.4} />
            <stop offset="95%" stopColor="var(--color-brand-500)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--chart-grid-1)" />
        <XAxis
          dataKey="ts"
          tickFormatter={(v) => formatKSTDate(v).slice(5)}
          tick={{ fill: 'var(--color-text-3)', fontSize: 11 }}
        />
        <YAxis
          tickFormatter={(v: number) => `${Math.round(v / 10000)}만`}
          tick={{ fill: 'var(--color-text-3)', fontSize: 11 }}
          width={48}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--color-bg-2)',
            border: '1px solid var(--color-border-2)',
            fontSize: 12,
          }}
          formatter={(value: number) => [formatCurrency(value), '평가자산']}
          labelFormatter={(label) => formatKSTDate(label as number)}
        />
        <Area
          type="monotone"
          dataKey="equity"
          stroke="var(--color-brand-500)"
          fill="url(#equityFill)"
          strokeWidth={1.6}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
