/**
 * ActivityFeed — 최근 활동 피드 (DSN-03 §1 대시보드 NotificationCenter inline)
 *
 * 시간순 이벤트 리스트. 타입별 아이콘·색·상대시간을 한글로 표시.
 */
import {
  Bell,
  BookOpen,
  CheckCircle2,
  ClipboardList,
  Library,
  Settings,
  UserPlus,
  type LucideIcon,
} from 'lucide-react';
import { type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Icon } from '../atoms/Icon';

export interface ActivityFeedItem {
  id: string;
  /** 자유 타입 — 외부에서 정의 */
  type: string;
  message: ReactNode;
  actorName?: string;
  contextLabel?: string;
  /** ISO timestamp */
  occurredAt: string;
  href?: string;
}

export interface ActivityFeedProps {
  items: ActivityFeedItem[];
  loading?: boolean;
  empty?: ReactNode;
  className?: string;
  /** 항목 클릭 콜백 */
  onSelect?: (item: ActivityFeedItem) => void;
}

const ICON_MAP: Record<string, { icon: LucideIcon; tone: string }> = {
  'member.registered': { icon: UserPlus, tone: 'text-success bg-success-50' },
  'library.created': { icon: Library, tone: 'text-info bg-info-50' },
  'code.updated': { icon: Settings, tone: 'text-warning bg-warning-50' },
  'loan.checkout': { icon: BookOpen, tone: 'text-primary-700 bg-primary-50' },
  'loan.return': { icon: CheckCircle2, tone: 'text-success bg-success-50' },
  'reservation.created': { icon: ClipboardList, tone: 'text-info bg-info-50' },
  system: { icon: Bell, tone: 'text-neutral-700 bg-neutral-100' },
};

function pickIcon(type: string) {
  return ICON_MAP[type] ?? ICON_MAP.system;
}

function relativeTime(iso: string, now = Date.now()): string {
  const t = new Date(iso).getTime();
  const diff = Math.max(0, now - t);
  const min = Math.floor(diff / 60000);
  if (min < 1) return '방금 전';
  if (min < 60) return `${min}분 전`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day}일 전`;
  return new Date(iso).toLocaleDateString('ko-KR');
}

export function ActivityFeed({
  items,
  loading,
  empty = '최근 활동이 없습니다.',
  className,
  onSelect,
}: ActivityFeedProps) {
  if (loading) {
    return (
      <ul className={cn('space-y-3', className)} aria-busy="true">
        {Array.from({ length: 4 }).map((_, i) => (
          <li key={i} className="h-12 animate-pulse rounded bg-neutral-100" />
        ))}
      </ul>
    );
  }
  if (!items.length) {
    return (
      <div className={cn('text-center text-[13px] text-neutral-500', className)}>{empty}</div>
    );
  }

  return (
    <ul className={cn('divide-y divide-neutral-100', className)} role="list">
      {items.map((item) => {
        const { icon, tone } = pickIcon(item.type);
        const Tag = onSelect || item.href ? 'button' : 'div';
        return (
          <li key={item.id}>
            <Tag
              type={onSelect ? 'button' : undefined}
              onClick={onSelect ? () => onSelect(item) : undefined}
              className={cn(
                'flex w-full items-start gap-3 py-3 text-left',
                (onSelect || item.href) &&
                  'hover:bg-neutral-50 focus-visible:outline-none focus-visible:bg-neutral-50',
              )}
            >
              <span
                className={cn(
                  'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full',
                  tone,
                )}
              >
                <Icon as={icon} size="sm" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] text-neutral-900">{item.message}</div>
                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-neutral-500">
                  {item.actorName && <span>{item.actorName}</span>}
                  {item.contextLabel && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span>{item.contextLabel}</span>
                    </>
                  )}
                  <span aria-hidden="true">·</span>
                  <time dateTime={item.occurredAt}>{relativeTime(item.occurredAt)}</time>
                </div>
              </div>
            </Tag>
          </li>
        );
      })}
    </ul>
  );
}
