/**
 * BarChartBlock — 카테고리 막대 차트
 */
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { seriesColor } from './chart-colors';

export interface BarSeries {
  dataKey: string;
  label: string;
  color?: string;
}

export interface BarChartBlockProps<T extends Record<string, unknown>> {
  data: T[];
  xKey: keyof T & string;
  series: BarSeries[];
  stacked?: boolean;
  ariaLabel?: string;
}

export function BarChartBlock<T extends Record<string, unknown>>({
  data,
  xKey,
  series,
  stacked = false,
  ariaLabel,
}: BarChartBlockProps<T>) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }} aria-label={ariaLabel}>
        <CartesianGrid stroke="var(--color-neutral-200, #e5e5e5)" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey={xKey}
          tick={{ fill: 'var(--color-neutral-600, #525252)', fontSize: 11 }}
          stroke="var(--color-neutral-300, #d4d4d4)"
        />
        <YAxis
          tick={{ fill: 'var(--color-neutral-600, #525252)', fontSize: 11 }}
          stroke="var(--color-neutral-300, #d4d4d4)"
          width={40}
        />
        <Tooltip
          cursor={{ fill: 'rgba(0,0,0,0.04)' }}
          contentStyle={{
            background: 'var(--surface-card, #ffffff)',
            border: '1px solid var(--color-neutral-200, #e5e5e5)',
            borderRadius: 6,
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 4 }} iconType="circle" iconSize={8} />
        {series.map((s, i) => (
          <Bar
            key={s.dataKey}
            dataKey={s.dataKey}
            name={s.label}
            stackId={stacked ? 'stack' : undefined}
            fill={s.color ?? seriesColor(i)}
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
