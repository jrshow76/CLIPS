'use client';

import { KpiCard, type KpiTone, type KpiTrend } from '@tulip/ui';
import { useDashboardSummaryQuery, type KpiMetric } from '@tulip/api-client';
import { BookOpen, AlertTriangle, UserPlus, BookMarked } from 'lucide-react';

const ICON_BY_KEY: Record<string, typeof BookOpen> = {
  loans_active: BookOpen,
  overdue: AlertTriangle,
  new_members: UserPlus,
  reservations: BookMarked,
};

function toTone(tone: KpiMetric['tone']): KpiTone {
  return (tone ?? 'neutral') as KpiTone;
}

function toTrend(trend: KpiMetric['trend']): KpiTrend {
  return trend;
}

export function KpiGrid({ libraryId }: { libraryId?: string }) {
  const { data, isLoading } = useDashboardSummaryQuery({ libraryId });
  const kpis = data?.kpis ?? [];

  if (isLoading && kpis.length === 0) {
    return (
      <section aria-label="핵심 지표" data-testid="dashboard-kpi-grid">
        <ul role="list" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <li key={i}>
              <KpiCard label="" value="" loading />
            </li>
          ))}
        </ul>
      </section>
    );
  }

  return (
    <section aria-label="핵심 지표" data-testid="dashboard-kpi-grid">
      <ul role="list" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((k) => (
          <li key={k.key}>
            <KpiCard
              label={k.label}
              value={k.value}
              delta={k.delta}
              deltaUnit={k.deltaUnit}
              trend={toTrend(k.trend)}
              tone={toTone(k.tone)}
              icon={ICON_BY_KEY[k.key]}
              sparkline={k.sparkline}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}
