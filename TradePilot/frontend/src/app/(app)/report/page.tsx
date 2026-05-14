'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Kpi } from '@/components/ui/kpi';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs } from '@/components/ui/tabs';
import { DataTable, type Column } from '@/components/ui/table';
import { PnlLineChart } from '@/components/charts/PnlLineChart';
import { ExportButton, ExportHistoryDrawer } from '@/components/exports';
import { useHoldings } from '@/lib/api/queries/dashboard';
import { usePnlReport } from '@/lib/api/queries/reports';
import { ROUTES } from '@/lib/constants';
import { formatCurrency, formatPct, formatPnl, pnlClass } from '@/lib/utils/format';
import type { Holding } from '@/types/portfolio';

type Period = '1M' | '3M' | '6M' | '1Y' | 'ALL';

export default function ReportPage() {
  const [period, setPeriod] = useState<Period>('3M');
  const report = usePnlReport(period);
  const holdings = useHoldings();

  // 기간 → ISO 날짜 변환 (서버 익스포트 필터로 전달)
  const exportFilters = useMemo(() => {
    const days = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365, ALL: 720 }[period];
    const to = new Date();
    const from = new Date();
    from.setDate(to.getDate() - days);
    return {
      from: from.toISOString().slice(0, 10),
      to: to.toISOString().slice(0, 10),
    };
  }, [period]);

  const holdingsColumns: Column<Holding>[] = [
    {
      key: 'name',
      header: '종목',
      cell: (h) => (
        <Link href={ROUTES.CHART(h.code)} className="hover:underline">
          <span className="fw-semibold">{h.name}</span>
          <span className="text-xs text-subtle ml-2">{h.code}</span>
        </Link>
      ),
      sortAccessor: 'name',
    },
    { key: 'qty', header: '수량', align: 'right', cell: (h) => `${h.qty}주`, sortAccessor: 'qty' },
    {
      key: 'avg_price',
      header: '평단가',
      align: 'right',
      cell: (h) => h.avg_price.toLocaleString('ko-KR'),
      sortAccessor: 'avg_price',
    },
    {
      key: 'current_price',
      header: '현재가',
      align: 'right',
      cell: (h) => h.current_price.toLocaleString('ko-KR'),
      sortAccessor: 'current_price',
    },
    {
      key: 'pnl',
      header: '평가손익',
      align: 'right',
      sortAccessor: 'pnl',
      cell: (h) => <span className={pnlClass(h.pnl)}>{formatPnl(h.pnl)}</span>,
    },
    {
      key: 'pnl_pct',
      header: '수익률',
      align: 'right',
      sortAccessor: 'pnl_pct',
      cell: (h) => <span className={pnlClass(h.pnl_pct)}>{formatPct(h.pnl_pct)}</span>,
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>수익률 리포트</h1>
          <p>기간별 평가자산과 손익을 분석합니다.</p>
        </div>
        <div className="row gap-2">
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
          <ExportButton
            jobType="PNL"
            filterParams={exportFilters}
            label="손익 다운로드"
          />
          <ExportButton
            jobType="ORDERS"
            filterParams={exportFilters}
            label="거래내역 다운로드"
            variant="ghost"
          />
        </div>
      </div>

      <div className="row gap-2 mb-3">
        <Link href={ROUTES.REPORT_TRADES}><Button variant="ghost">거래 내역 →</Button></Link>
        <Link href={ROUTES.REPORT_STRATEGIES}><Button variant="ghost">전략별 성과 →</Button></Link>
        <ExportHistoryDrawer />
      </div>

      {report.isError && <ErrorCard message="리포트 데이터를 불러올 수 없습니다." />}

      {report.data && (
        <>
          <section className="grid-cols-4 mb-4">
            <Card><Card.Body>
              <Kpi
                label="총 손익"
                value={<span className={pnlClass(report.data.summary.total_pnl)}>{formatPnl(report.data.summary.total_pnl)}</span>}
              />
            </Card.Body></Card>
            <Card><Card.Body>
              <Kpi
                label="총 수익률"
                value={<span className={pnlClass(report.data.summary.total_pnl_pct)}>{formatPct(report.data.summary.total_pnl_pct)}</span>}
              />
            </Card.Body></Card>
            <Card><Card.Body><Kpi label="승률" value={`${report.data.summary.win_rate.toFixed(1)}%`} /></Card.Body></Card>
            <Card><Card.Body><Kpi label="거래 횟수" value={`${report.data.summary.trades}건`} /></Card.Body></Card>
          </section>

          <Card className="mb-4">
            <Card.Header
              title="평가자산 추이"
              right={<Badge variant="info">{period}</Badge>}
            />
            <Card.Body>
              <PnlLineChart data={report.data.series} />
            </Card.Body>
          </Card>

          <div className="grid-cols-2 mb-4">
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

          <Card>
            <Card.Header title="종목별 손익" />
            <Card.Body className="p-0">
              {holdings.data && (
                <DataTable
                  columns={holdingsColumns}
                  data={holdings.data}
                  rowKey={(h) => h.code}
                  pageSize={20}
                />
              )}
            </Card.Body>
          </Card>
        </>
      )}

      {report.isLoading && <Skeleton height={400} />}
    </>
  );
}
