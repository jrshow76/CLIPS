'use client';

import { Line, LineChart, ResponsiveContainer } from 'recharts';

import { cn } from '@/lib/utils/cn';

export interface StockSparklineProps {
  data: { ts: number; close: number }[];
  width?: number | string;
  height?: number;
  className?: string;
  /** 양수면 빨강, 음수면 파랑 */
  delta?: number;
}

/**
 * 미니 차트(스파크라인). 보유종목 행, 추천주 카드, 시장 요약 미니에 사용.
 * - 축/툴팁 없음, 단일 라인.
 */
export function StockSparkline({ data, width = '100%', height = 36, className, delta = 0 }: StockSparklineProps) {
  const color = delta >= 0 ? 'var(--color-up)' : 'var(--color-down)';
  return (
    <div className={cn('block', className)} style={{ width }}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <Line type="monotone" dataKey="close" stroke={color} dot={false} strokeWidth={1.4} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
