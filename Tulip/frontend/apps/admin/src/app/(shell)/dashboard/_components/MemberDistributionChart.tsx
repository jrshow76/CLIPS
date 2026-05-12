'use client';

import { ChartContainer, DonutChartBlock, type DonutDatum } from '@tulip/ui';
import { useDashboardSummaryQuery } from '@tulip/api-client';

export function MemberDistributionChart({ libraryId }: { libraryId?: string }) {
  const { data, isLoading, error, refetch } = useDashboardSummaryQuery({ libraryId });
  const dist = data?.memberTypeDistribution ?? [];
  const donutData: DonutDatum[] = dist.map((d) => ({ name: d.label, value: d.count }));
  const total = donutData.reduce((s, d) => s + d.value, 0);

  return (
    <ChartContainer
      title="회원 유형 분포"
      description="현재 활성 회원 기준"
      height={280}
      loading={isLoading}
      error={error ? { message: error.message, onRetry: () => refetch() } : null}
      empty={!isLoading && total === 0}
    >
      <DonutChartBlock
        data={donutData}
        centerLabel="전체"
        centerValue={total.toLocaleString('ko-KR')}
        ariaLabel="회원 유형별 분포"
      />
    </ChartContainer>
  );
}
