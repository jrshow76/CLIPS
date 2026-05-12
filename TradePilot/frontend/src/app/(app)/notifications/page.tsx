'use client';

import { CheckCheck } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs } from '@/components/ui/tabs';
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from '@/lib/api/queries/notifications';
import { formatKST, formatRelativeKR } from '@/lib/utils/date';
import type { AppNotification, NotificationVariant } from '@/types/notification';

type Filter = 'ALL' | 'UNREAD' | NotificationVariant;

const VARIANT_LABEL: Record<NotificationVariant, { label: string; variant: 'info' | 'success' | 'warning' | 'danger' | 'default' }> = {
  SIGNAL: { label: '시그널', variant: 'info' },
  FILL: { label: '체결', variant: 'success' },
  LIMIT: { label: '한도', variant: 'warning' },
  SYSTEM: { label: '시스템', variant: 'default' },
  BACKTEST: { label: '백테스트', variant: 'info' },
  NEWS: { label: '뉴스', variant: 'default' },
};

export default function NotificationsPage() {
  const [filter, setFilter] = useState<Filter>('ALL');
  const notis = useNotifications();
  const markOne = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();

  const filtered = (notis.data ?? []).filter((n) => {
    if (filter === 'ALL') return true;
    if (filter === 'UNREAD') return !n.read;
    return n.variant === filter;
  });

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>알림 센터</h1>
          <p>최근 알림을 확인하고 처리합니다.</p>
        </div>
        <div className="row gap-2">
          <Button
            variant="outline"
            leftIcon={<CheckCheck className="h-4 w-4" />}
            onClick={() => markAll.mutate()}
            loading={markAll.isPending}
          >
            모두 읽음
          </Button>
        </div>
      </div>

      <Tabs<Filter>
        value={filter}
        onChange={setFilter}
        items={[
          { value: 'ALL', label: '전체' },
          { value: 'UNREAD', label: '읽지 않음', count: notis.data?.filter((n) => !n.read).length },
          { value: 'SIGNAL', label: '시그널' },
          { value: 'FILL', label: '체결' },
          { value: 'LIMIT', label: '한도' },
          { value: 'SYSTEM', label: '시스템' },
          { value: 'BACKTEST', label: '백테스트' },
        ]}
      />

      {notis.isLoading && <Skeleton height={300} />}
      {notis.isError && <ErrorCard message="알림을 불러올 수 없습니다." />}
      {notis.data && filtered.length === 0 && (
        <EmptyState title="표시할 알림이 없습니다." description="조건을 변경해 보세요." />
      )}

      <Card>
        <Card.Body className="p-0">
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {filtered.map((n) => (
              <NotificationItem key={n.id} noti={n} onMarkRead={() => markOne.mutate(n.id)} />
            ))}
          </ul>
        </Card.Body>
      </Card>
    </>
  );
}

function NotificationItem({ noti, onMarkRead }: { noti: AppNotification; onMarkRead: () => void }) {
  const meta = VARIANT_LABEL[noti.variant];
  const inner = (
    <div className="row gap-3 items-start">
      <Badge variant={meta.variant}>{meta.label}</Badge>
      <div className="flex-1">
        <p className="text-strong fw-semibold">{noti.title}</p>
        <p className="text-sm text-muted">{noti.message}</p>
        <p className="text-subtle text-xs mt-1">
          {formatRelativeKR(noti.created_at)} · {formatKST(noti.created_at)}
        </p>
      </div>
      {!noti.read && <span className="badge badge-dot" style={{ background: 'var(--color-brand-500)' }} />}
    </div>
  );

  return (
    <li
      style={{
        padding: 'var(--space-4)',
        borderBottom: '1px solid var(--color-border-1)',
        background: noti.read ? undefined : 'var(--color-bg-2)',
      }}
    >
      {noti.link ? (
        <Link href={noti.link} onClick={() => !noti.read && onMarkRead()}>
          {inner}
        </Link>
      ) : (
        <button
          type="button"
          onClick={() => !noti.read && onMarkRead()}
          style={{ background: 'none', border: 'none', textAlign: 'left', width: '100%' }}
        >
          {inner}
        </button>
      )}
    </li>
  );
}
