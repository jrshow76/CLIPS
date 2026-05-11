import { Badge } from '@tulip/ui';

interface Kpi {
  label: string;
  value: string;
  delta?: string;
  tone: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
}

const items: Kpi[] = [
  { label: '오늘 대출', value: '342', delta: '+12%', tone: 'success' },
  { label: '오늘 반납', value: '305', delta: '+8%', tone: 'info' },
  { label: '연체', value: '27', delta: '-5%', tone: 'warning' },
  { label: '예약 대기', value: '58', tone: 'neutral' },
];

export function KpiGrid() {
  return (
    <section aria-label="핵심 지표">
      <ul role="list" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => (
          <li
            key={item.label}
            className="rounded-lg border border-neutral-200 bg-surface-card p-4 shadow-sm"
          >
            <div className="text-[12px] font-semibold uppercase tracking-wider text-neutral-500">
              {item.label}
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-[28px] font-bold tabular-nums text-neutral-900">
                {item.value}
              </span>
              {item.delta && (
                <Badge tone={item.tone} variant="soft" size="sm">
                  {item.delta}
                </Badge>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
