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
import type { SectorFlowSeries } from '@/types/sector-flow';

const COLORS = ['#2f5cff', '#10b981', '#ef4444', '#f59e0b', '#6366f1', '#06b6d4'];

export function SectorFlowChart({ data, height = 280 }: { data: SectorFlowSeries[]; height?: number }) {
  if (!data.length) return null;
  // 시간축 기준 병합
  const ts = data[0]!.points.map((p) => p.ts);
  const merged = ts.map((t, idx) => {
    const row: Record<string, number | string> = { ts: t };
    data.forEach((series) => {
      row[series.name] = series.points[idx]?.net ?? 0;
    });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={merged} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--chart-grid-1)" />
        <XAxis
          dataKey="ts"
          tickFormatter={(v) => formatKSTDate(v).slice(5)}
          tick={{ fill: 'var(--color-text-3)', fontSize: 11 }}
        />
        <YAxis tick={{ fill: 'var(--color-text-3)', fontSize: 11 }} width={48} />
        <Tooltip
          contentStyle={{ background: 'var(--color-bg-2)', border: '1px solid var(--color-border-2)', fontSize: 12 }}
          labelFormatter={(v) => formatKSTDate(v as number)}
          formatter={(value: number) => [`${value.toLocaleString('ko-KR')}억`, '순매수']}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {data.map((series, i) => (
          <Line
            key={series.code}
            type="monotone"
            dataKey={series.name}
            stroke={COLORS[i % COLORS.length]}
            dot={false}
            strokeWidth={1.4}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
