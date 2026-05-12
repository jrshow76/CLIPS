/**
 * KpiCard — 핵심 지표 카드 (DSN-03 §1 대시보드 StatCard)
 *
 * 표시:
 *   - 라벨, 값(큰 숫자), delta, trend 아이콘
 *   - 옵션: sparkline (작은 라인 차트)
 *   - 옵션: 아이콘
 *
 * 사용 예:
 *   <KpiCard label="대출 중" value={342} delta={12} deltaUnit="percent" trend="up" tone="primary" />
 */
import { ArrowDownRight, ArrowRight, ArrowUpRight, type LucideIcon } from 'lucide-react';
import { Line, LineChart, ResponsiveContainer, YAxis } from 'recharts';
import { type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Icon } from '../atoms/Icon';
import { Skeleton } from '../atoms/Skeleton';

export type KpiTone =
  | 'neutral'
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info';

export type KpiTrend = 'up' | 'down' | 'flat';

export interface KpiCardProps {
  label: string;
  /** 큰 숫자 (number/string 모두 허용) */
  value: number | string;
  /** 비교 기준 대비 변화량 */
  delta?: number;
  /** delta 단위 — 절대수 또는 퍼센트 */
  deltaUnit?: 'count' | 'percent';
  trend?: KpiTrend;
  tone?: KpiTone;
  icon?: LucideIcon;
  /** sparkline 데이터 (7개 내외 권장) */
  sparkline?: number[];
  /** 로딩 상태 */
  loading?: boolean;
  /** 클릭 → 드릴다운 */
  onClick?: () => void;
  /** 추가 보조 텍스트 (예: 평년 대비) */
  footer?: ReactNode;
  className?: string;
}

const toneAccent: Record<KpiTone, string> = {
  neutral: 'text-neutral-700',
  primary: 'text-primary-700',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
  info: 'text-info',
};

const toneSpark: Record<KpiTone, string> = {
  neutral: 'var(--color-neutral-500, #737373)',
  primary: 'var(--color-primary-500, #db2777)',
  success: 'var(--color-success, #16a34a)',
  warning: 'var(--color-warning, #d97706)',
  danger: 'var(--color-danger, #dc2626)',
  info: 'var(--color-info, #0284c7)',
};

const trendIconMap: Record<KpiTrend, LucideIcon> = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  flat: ArrowRight,
};

const trendColorMap: Record<KpiTrend, string> = {
  up: 'text-success',
  down: 'text-danger',
  flat: 'text-neutral-500',
};

function formatDelta(delta?: number, unit?: 'count' | 'percent'): string | null {
  if (delta === undefined || delta === null) return null;
  const sign = delta > 0 ? '+' : '';
  if (unit === 'percent') return `${sign}${delta}%`;
  return `${sign}${delta}`;
}

export function KpiCard({
  label,
  value,
  delta,
  deltaUnit,
  trend = 'flat',
  tone = 'neutral',
  icon,
  sparkline,
  loading = false,
  onClick,
  footer,
  className,
}: KpiCardProps) {
  const Tag = onClick ? 'button' : 'div';
  const TrendIcon = trendIconMap[trend];
  const deltaLabel = formatDelta(delta, deltaUnit);
  const sparkData = sparkline?.map((v, i) => ({ i, v })) ?? null;

  if (loading) {
    return (
      <div
        className={cn(
          'rounded-lg border border-neutral-200 bg-surface-card p-4 shadow-sm',
          className,
        )}
        aria-busy="true"
      >
        <Skeleton className="h-3 w-24" />
        <Skeleton className="mt-3 h-8 w-32" />
        <Skeleton className="mt-3 h-3 w-16" />
      </div>
    );
  }

  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      aria-label={`${label} ${value}`}
      className={cn(
        'group block w-full rounded-lg border border-neutral-200 bg-surface-card p-4 text-left shadow-sm transition-colors',
        onClick && 'hover:border-primary-300 focus-visible:outline-none focus-visible:shadow-focus',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="text-[12px] font-semibold uppercase tracking-wider text-neutral-500">
          {label}
        </div>
        {icon && (
          <span className={cn('shrink-0', toneAccent[tone])}>
            <Icon as={icon} size="sm" />
          </span>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className={cn('text-[28px] font-bold tabular-nums text-neutral-900')}>
          {value}
        </span>
        {deltaLabel && (
          <span
            className={cn(
              'inline-flex items-center gap-0.5 text-[12px] font-semibold',
              trendColorMap[trend],
            )}
          >
            <Icon as={TrendIcon} size="xs" />
            {deltaLabel}
          </span>
        )}
      </div>
      {sparkData && sparkData.length > 1 && (
        <div className="mt-3 h-10" aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparkData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
              <YAxis hide domain={['dataMin', 'dataMax']} />
              <Line
                type="monotone"
                dataKey="v"
                stroke={toneSpark[tone]}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {footer && <div className="mt-2 text-[12px] text-neutral-500">{footer}</div>}
    </Tag>
  );
}
