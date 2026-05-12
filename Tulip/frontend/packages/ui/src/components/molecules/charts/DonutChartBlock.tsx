/**
 * DonutChartBlock — 비율 도넛 차트
 *
 * - 가운데 빈 공간에 totalLabel/totalValue를 표시할 수 있음
 */
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { type ReactNode } from 'react';

import { seriesColor } from './chart-colors';

export interface DonutDatum {
  /** 표시 라벨 (legend·tooltip) */
  name: string;
  value: number;
  color?: string;
}

export interface DonutChartBlockProps {
  data: DonutDatum[];
  /** 중앙 라벨 (예: "전체") */
  centerLabel?: ReactNode;
  /** 중앙 값 (예: 3005) — 생략시 자동 합산 */
  centerValue?: ReactNode;
  /** 내부 반지름 비율 (0~1) */
  innerRadiusRatio?: number;
  ariaLabel?: string;
}

export function DonutChartBlock({
  data,
  centerLabel,
  centerValue,
  innerRadiusRatio = 0.6,
  ariaLabel,
}: DonutChartBlockProps) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const displayTotal = centerValue ?? total.toLocaleString();

  return (
    <div className="relative h-full w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart aria-label={ariaLabel}>
          <Tooltip
            contentStyle={{
              background: 'var(--surface-card, #ffffff)',
              border: '1px solid var(--color-neutral-200, #e5e5e5)',
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(v: number, n: string) => [`${v.toLocaleString()}건`, n]}
          />
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={`${Math.round(innerRadiusRatio * 100)}%`}
            outerRadius="100%"
            paddingAngle={2}
            stroke="var(--surface-card, #ffffff)"
            strokeWidth={2}
            isAnimationActive={false}
          >
            {data.map((entry, i) => (
              <Cell key={entry.name} fill={entry.color ?? seriesColor(i)} />
            ))}
          </Pie>
          <Legend
            verticalAlign="bottom"
            wrapperStyle={{ fontSize: 12 }}
            iconType="circle"
            iconSize={8}
          />
        </PieChart>
      </ResponsiveContainer>
      <div
        className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
        style={{ marginBottom: 28 /* legend 영역 보정 */ }}
        aria-hidden="true"
      >
        {centerLabel && (
          <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
            {centerLabel}
          </span>
        )}
        <span className="text-[20px] font-bold tabular-nums text-neutral-900">
          {displayTotal}
        </span>
      </div>
    </div>
  );
}
