'use client';

import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Skeleton } from '@/components/ui/skeleton';
import { DataTable, type Column } from '@/components/ui/table';
import { useStrategyPerformance } from '@/lib/api/queries/trades';
import { ROUTES } from '@/lib/constants';
import { formatPct, formatPnl, pnlClass } from '@/lib/utils/format';
import type { MockStrategyPerformance } from '@/lib/mocks/data';

export default function ReportStrategiesPage() {
  const perf = useStrategyPerformance();

  const columns: Column<MockStrategyPerformance>[] = [
    {
      key: 'strategy_name',
      header: '전략',
      cell: (p) => (
        <Link href={ROUTES.AUTO_TRADING_DETAIL(p.strategy_id)} className="hover:underline">
          <span className="fw-semibold">{p.strategy_name}</span>
        </Link>
      ),
      sortAccessor: 'strategy_name',
    },
    {
      key: 'status',
      header: '상태',
      cell: (p) => (
        <Badge variant={p.status === 'ACTIVE' ? 'success' : p.status === 'PAUSED' ? 'warning' : 'default'}>
          {p.status === 'ACTIVE' ? '실행 중' : p.status === 'PAUSED' ? '일시정지' : '보관'}
        </Badge>
      ),
    },
    { key: 'trades', header: '거래수', align: 'right', cell: (p) => `${p.trades}건`, sortAccessor: 'trades' },
    { key: 'win_rate', header: '승률', align: 'right', cell: (p) => `${p.win_rate.toFixed(1)}%`, sortAccessor: 'win_rate' },
    {
      key: 'total_pnl',
      header: '누적 손익',
      align: 'right',
      sortAccessor: 'total_pnl',
      cell: (p) => <span className={pnlClass(p.total_pnl)}>{formatPnl(p.total_pnl)}</span>,
    },
    {
      key: 'total_pnl_pct',
      header: '수익률',
      align: 'right',
      sortAccessor: 'total_pnl_pct',
      cell: (p) => <span className={pnlClass(p.total_pnl_pct)}>{formatPct(p.total_pnl_pct)}</span>,
    },
    {
      key: 'mdd_pct',
      header: 'MDD',
      align: 'right',
      sortAccessor: 'mdd_pct',
      cell: (p) => <span className="text-down">{formatPct(p.mdd_pct)}</span>,
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>전략별 성과 비교</h1>
          <p>활성 전략의 누적 손익, 승률, MDD를 한눈에 확인합니다.</p>
        </div>
        <Link href={ROUTES.REPORT}><Button variant="outline">← 리포트</Button></Link>
      </div>

      {perf.isLoading && <Skeleton height={200} />}
      {perf.isError && <ErrorCard message="성과 데이터를 불러올 수 없습니다." />}

      {perf.data && (
        <Card>
          <Card.Body className="p-0">
            <DataTable columns={columns} data={perf.data} rowKey={(p) => p.strategy_id} />
          </Card.Body>
        </Card>
      )}
    </>
  );
}
