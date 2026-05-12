'use client';

import { useState } from 'react';

import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Kpi } from '@/components/ui/kpi';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs } from '@/components/ui/tabs';
import { PnlLineChart } from '@/components/charts/PnlLineChart';
import { usePnlReport } from '@/lib/api/queries/reports';
import { formatCurrency, formatPct, formatPnl, pnlClass } from '@/lib/utils/format';

type Period = '1M' | '3M' | '6M' | '1Y' | 'ALL';

export default function ReportPage() {
  const [period, setPeriod] = useState<Period>('3M');
  const report = usePnlReport(period);

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>수익률 리포트</h1>
          <p>기간별 평가자산과 손익을 분석합니다.</p>
        </div>
        <Tabs
          variant="pill"
          value={period}
          onChange={setPeriod}
          items={[
            { value: '1M', label: '1개월' },
            { value: '3M', label: '3개월' },
            { value: '6M', label: '6개월' },
            { value: '1Y', label: '1년' },
            { value: 'ALL', label: '전체' },
          ]}
        />
      </div>

      {report.isError && <ErrorCard message="리포트 데이터를 불러올 수 없습니다." />}

      {report.data && (
        <>
          <section className="grid-cols-4 mb-4">
            <Card><Card.Body><Kpi
              label="총 손익"
              value={<span className={pnlClass(report.data.summary.total_pnl)}>{formatPnl(report.data.summary.total_pnl)}</span>}
            /></Card.Body></Card>
            <Card><Card.Body><Kpi
              label="총 수익률"
              value={<span className={pnlClass(report.data.summary.total_pnl_pct)}>{formatPct(report.data.summary.total_pnl_pct)}</span>}
            /></Card.Body></Card>
            <Card><Card.Body><Kpi label="승률" value={`${report.data.summary.win_rate.toFixed(1)}%`} /></Card.Body></Card>
            <Card><Card.Body><Kpi label="거래 횟수" value={`${report.data.summary.trades}건`} /></Card.Body></Card>
          </section>

          <Card>
            <Card.Header title="평가자산 추이" />
            <Card.Body>
              <PnlLineChart data={report.data.series} />
            </Card.Body>
          </Card>

          <div className="grid-cols-2 mt-4">
            <Card>
              <Card.Header title="최고 거래" />
              <Card.Body>
                <p className="kpi__value text-up">{formatCurrency(report.data.summary.best_trade ?? 0)}</p>
              </Card.Body>
            </Card>
            <Card>
              <Card.Header title="최악 거래" />
              <Card.Body>
                <p className="kpi__value text-down">{formatCurrency(report.data.summary.worst_trade ?? 0)}</p>
              </Card.Body>
            </Card>
          </div>
        </>
      )}

      {report.isLoading && <Skeleton height={400} />}
    </>
  );
}
