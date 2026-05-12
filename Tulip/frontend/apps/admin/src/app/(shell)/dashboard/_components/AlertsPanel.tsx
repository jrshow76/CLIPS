'use client';

import { AlertPanel, type AlertPanelItem } from '@tulip/ui';
import { useDashboardSummaryQuery } from '@tulip/api-client';

export function AlertsPanel({ libraryId }: { libraryId?: string }) {
  const { data, isLoading } = useDashboardSummaryQuery({ libraryId });
  const items: AlertPanelItem[] = (data?.alerts ?? []).map((a) => ({
    id: a.id,
    severity: a.severity,
    title: a.title,
    description: a.description,
    href: a.href,
    occurredAt: a.occurredAt,
  }));

  return (
    <section
      aria-label="알림"
      className="rounded-lg border border-neutral-200 bg-surface-card p-4 shadow-sm"
    >
      <header className="mb-3">
        <h3 className="text-[15px] font-semibold text-neutral-900">알림</h3>
        <p className="text-[12px] text-neutral-500">조치가 필요한 항목</p>
      </header>
      <AlertPanel items={items} loading={isLoading} />
    </section>
  );
}
