import { PageHeader } from '@tulip/ui';

import { KpiGrid } from './_components/KpiGrid';
import { LoanTrendsChart } from './_components/LoanTrendsChart';
import { MemberDistributionChart } from './_components/MemberDistributionChart';
import { RecentActivities } from './_components/RecentActivities';
import { AlertsPanel } from './_components/AlertsPanel';
import { TopMembersCard } from './_components/TopMembersCard';

export const metadata = { title: '대시보드 — Tulip+ Admin' };

export default function DashboardPage() {
  return (
    <>
      <PageHeader
        title="대시보드"
        description="오늘의 운영 현황 요약입니다."
        breadcrumb={[{ label: '홈', href: '/' }, { label: '대시보드' }]}
      />
      <div className="space-y-6 p-6">
        <KpiGrid />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <LoanTrendsChart />
          </div>
          <div>
            <MemberDistributionChart />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <RecentActivities />
          <AlertsPanel />
          <TopMembersCard />
        </div>
      </div>
    </>
  );
}
