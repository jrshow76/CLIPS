/**
 * AlertPanel — 알림 카드 묶음 (severity 별 색)
 *
 * 사용 예: 대시보드 우측 패널에서 연체·재고·시설 알림 모음을 표시.
 */
import { AlertOctagon, AlertTriangle, Info, type LucideIcon } from 'lucide-react';
import { type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Icon } from '../atoms/Icon';

export type AlertSeverity = 'info' | 'warning' | 'danger';

export interface AlertPanelItem {
  id: string;
  severity: AlertSeverity;
  title: ReactNode;
  description?: ReactNode;
  href?: string;
  /** 우측 액션 라벨 (기본: "확인") */
  actionLabel?: string;
  /** 발생 시각 (ISO) — 표시용 */
  occurredAt?: string;
}

export interface AlertPanelProps {
  items: AlertPanelItem[];
  loading?: boolean;
  empty?: ReactNode;
  onSelect?: (item: AlertPanelItem) => void;
  className?: string;
}

const SEVERITY_STYLES: Record<AlertSeverity, { wrap: string; icon: LucideIcon; iconColor: string }> = {
  info: {
    wrap: 'border-info-50 bg-info-50/40',
    icon: Info,
    iconColor: 'text-info',
  },
  warning: {
    wrap: 'border-warning-50 bg-warning-50/40',
    icon: AlertTriangle,
    iconColor: 'text-warning',
  },
  danger: {
    wrap: 'border-danger-50 bg-danger-50/40',
    icon: AlertOctagon,
    iconColor: 'text-danger',
  },
};

export function AlertPanel({
  items,
  loading,
  empty = '현재 알림이 없습니다.',
  onSelect,
  className,
}: AlertPanelProps) {
  if (loading) {
    return (
      <ul className={cn('space-y-2', className)} aria-busy="true">
        {Array.from({ length: 3 }).map((_, i) => (
          <li key={i} className="h-16 animate-pulse rounded-md bg-neutral-100" />
        ))}
      </ul>
    );
  }
  if (!items.length) {
    return (
      <div className={cn('rounded-md border border-dashed border-neutral-300 p-4 text-center text-[13px] text-neutral-500', className)}>
        {empty}
      </div>
    );
  }

  return (
    <ul className={cn('space-y-2', className)} role="list">
      {items.map((item) => {
        const sev = SEVERITY_STYLES[item.severity];
        const Tag = onSelect || item.href ? 'button' : 'div';
        return (
          <li key={item.id}>
            <Tag
              type={onSelect ? 'button' : undefined}
              onClick={onSelect ? () => onSelect(item) : undefined}
              className={cn(
                'flex w-full items-start gap-3 rounded-md border p-3 text-left',
                sev.wrap,
                (onSelect || item.href) &&
                  'hover:brightness-95 focus-visible:outline-none focus-visible:shadow-focus',
              )}
            >
              <span className={cn('mt-0.5 shrink-0', sev.iconColor)}>
                <Icon as={sev.icon} size="sm" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-semibold text-neutral-900">{item.title}</div>
                {item.description && (
                  <p className="mt-0.5 text-[12px] text-neutral-700">{item.description}</p>
                )}
              </div>
              {item.actionLabel && (
                <span className="shrink-0 text-[12px] font-medium text-primary-700">
                  {item.actionLabel}
                </span>
              )}
            </Tag>
          </li>
        );
      })}
    </ul>
  );
}
