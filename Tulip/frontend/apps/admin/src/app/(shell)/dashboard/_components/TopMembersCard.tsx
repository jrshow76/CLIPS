'use client';

import { Skeleton } from '@tulip/ui';
import { useTopMembersQuery } from '@tulip/api-client';

export function TopMembersCard({ libraryId }: { libraryId?: string }) {
  const { data, isLoading } = useTopMembersQuery({ limit: 5, libraryId });
  const rows = data ?? [];

  return (
    <section
      aria-label="활동 회원 Top 5"
      className="rounded-lg border border-neutral-200 bg-surface-card p-4 shadow-sm"
    >
      <header className="mb-3">
        <h3 className="text-[15px] font-semibold text-neutral-900">활동 회원 Top 5</h3>
        <p className="text-[12px] text-neutral-500">이번 달 대출 건수 기준</p>
      </header>
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="py-6 text-center text-[13px] text-neutral-500">표시할 회원이 없습니다.</p>
      ) : (
        <ol className="divide-y divide-neutral-100">
          {rows.map((m, idx) => (
            <li
              key={m.memberId}
              className="flex items-center justify-between gap-3 py-2.5"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-50 text-[12px] font-semibold text-primary-700">
                  {idx + 1}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-[14px] font-medium text-neutral-900">{m.name}</p>
                  <p className="truncate text-[12px] text-neutral-500">
                    {m.memberNumber} · {m.libraryName}
                  </p>
                </div>
              </div>
              <div className="shrink-0 text-right tabular-nums">
                <p className="text-[14px] font-semibold text-neutral-900">
                  {m.loans.toLocaleString('ko-KR')}건
                </p>
                <p className="text-[11px] text-neutral-500">대출 중 {m.active}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
