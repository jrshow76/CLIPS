import { Badge, PageHeader } from '@tulip/ui';

import { KpiGrid } from './_components/KpiGrid';

export const metadata = { title: '대시보드 — Tulip+ Admin' };

export default function DashboardPage() {
  return (
    <>
      <PageHeader
        title="대시보드"
        description="오늘의 운영 현황 요약입니다."
        breadcrumb={[{ label: '홈', href: '/' }, { label: '대시보드' }]}
        actions={
          <Badge tone="primary" variant="soft">
            Phase 1-A 자리표시자
          </Badge>
        }
      />
      <div className="p-6">
        <KpiGrid />
      </div>
    </>
  );
}
