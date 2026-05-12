'use client';

import { ActivityFeed, type ActivityFeedItem } from '@tulip/ui';
import { useRecentActivitiesQuery } from '@tulip/api-client';

export function RecentActivities({ libraryId }: { libraryId?: string }) {
  const { data, isLoading } = useRecentActivitiesQuery({ limit: 10, libraryId });
  const items: ActivityFeedItem[] = (data ?? []).map((e) => ({
    id: e.id,
    type: e.type,
    message: e.message,
    actorName: e.actorName,
    contextLabel: e.contextLabel,
    occurredAt: e.occurredAt,
  }));

  return (
    <section
      aria-label="최근 활동"
      className="rounded-lg border border-neutral-200 bg-surface-card p-4 shadow-sm"
    >
      <header className="mb-3">
        <h3 className="text-[15px] font-semibold text-neutral-900">최근 활동</h3>
        <p className="text-[12px] text-neutral-500">사용자·시스템 이벤트</p>
      </header>
      <ActivityFeed items={items} loading={isLoading} />
    </section>
  );
}
