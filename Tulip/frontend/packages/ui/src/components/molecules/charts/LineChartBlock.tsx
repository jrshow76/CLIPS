/**
 * LineChartBlock — 시계열 라인 차트 (Recharts wrap)
 *
 * - 다중 시리즈 지원 (props.series)
 * - x축은 라벨 자동 (xKey 지정)
 * - 접근성: aria-label 권장
 */
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

import { seriesColor } from './chart-colors';

export interface LineSeries {
  dataKey: string;
  label: string;
  color?: string;
  strokeDasharray?: string;
}

export interface LineChartBlockProps<T extends Record<string, unknown>> {
  data: T[];
  xKey: keyof T & string;
  series: LineSeries[];
  /** 부드러운 곡선 */
  smooth?: boolean;
  /** 점 표시 */
  dots?: boolean;
  /** Y축 단위 라벨 */
  yUnit?: string;
  ariaLabel?: string;
  /** x축 라벨 포맷터 */
  xTickFormatter?: (v: string) => string;
}

export function LineChartBlock<T extends Record<string, unknown>>({
  data,
  xKey,
  series,
  smooth = true,
  dots = false,
  yUnit,
  ariaLabel,
  xTickFormatter,
}: LineChartBlockProps<T>) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }} aria-label={ariaLabel}>
        <CartesianGrid stroke="var(--color-neutral-200, #e5e5e5)" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey={xKey}
          tick={{ fill: 'var(--color-neutral-600, #525252)', fontSize: 11 }}
          tickFormatter={xTickFormatter}
          tickMargin={6}
          stroke="var(--color-neutral-300, #d4d4d4)"
        />
        <YAxis
          tick={{ fill: 'var(--color-neutral-600, #525252)', fontSize: 11 }}
          tickFormatter={(v: number) => (yUnit ? `${v}${yUnit}` : `${v}`)}
          stroke="var(--color-neutral-300, #d4d4d4)"
          width={40}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--surface-card, #ffffff)',
            border: '1px solid var(--color-neutral-200, #e5e5e5)',
            borderRadius: 6,
            fontSize: 12,
          }}
          labelStyle={{ color: 'var(--color-neutral-700, #404040)', fontWeight: 600 }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 4 }}
          iconType="circle"
          iconSize={8}
        />
        {series.map((s, i) => (
          <Line
            key={s.dataKey}
            type={smooth ? 'monotone' : 'linear'}
            dataKey={s.dataKey}
            name={s.label}
            stroke={s.color ?? seriesColor(i)}
            strokeWidth={2}
            strokeDasharray={s.strokeDasharray}
            dot={dots}
            activeDot={{ r: 4 }}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
