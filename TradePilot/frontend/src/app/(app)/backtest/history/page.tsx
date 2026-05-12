'use client';

import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Skeleton } from '@/components/ui/skeleton';
import { DataTable, type Column } from '@/components/ui/table';
import { useBacktestHistory } from '@/lib/api/queries/backtest-history';
import { ROUTES } from '@/lib/constants';
import { formatKST } from '@/lib/utils/date';
import { formatCurrency, formatPct, pnlClass } from '@/lib/utils/format';
import type { MockBacktestHistoryItem } from '@/lib/mocks/data';

export default function BacktestHistoryPage() {
  const history = useBacktestHistory();

  const columns: Column<MockBacktestHistoryItem>[] = [
    {
      key: 'created_at',
      header: '실행 시각',
      sortAccessor: 'created_at',
      cell: (h) => formatKST(h.created_at),
    },
    {
      key: 'strategy_name',
      header: '전략',
      cell: (h) => <span className="fw-semibold">{h.strategy_name}</span>,
      sortAccessor: 'strategy_name',
    },
    { key: 'period', header: '기간', cell: (h) => `${h.from} ~ ${h.to}` },
    {
      key: 'initial_cash',
      header: '초기 자본',
      align: 'right',
      cell: (h) => formatCurrency(h.initial_cash),
    },
    {
      key: 'total_return_pct',
      header: '수익률',
      align: 'right',
      sortAccessor: 'total_return_pct',
      cell: (h) => <span className={pnlClass(h.total_return_pct)}>{formatPct(h.total_return_pct)}</span>,
    },
    {
      key: 'mdd_pct',
      header: 'MDD',
      align: 'right',
      sortAccessor: 'mdd_pct',
      cell: (h) => <span className="text-down">{formatPct(h.mdd_pct)}</span>,
    },
    {
      key: 'status',
      header: '상태',
      cell: (h) => (
        <Badge variant={h.status === 'DONE' ? 'success' : h.status === 'FAILED' ? 'danger' : 'info'}>
          {h.status}
        </Badge>
      ),
    },
    {
      key: 'action',
      header: '',
      align: 'right',
      cell: (h) => (
        <Link href={ROUTES.BACKTEST_DETAIL(h.job_id)}>
          <Button variant="outline" size="sm">결과 →</Button>
        </Link>
      ),
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>과거 백테스트</h1>
          <p>이전에 실행한 백테스트 결과를 다시 확인합니다.</p>
        </div>
        <Link href={ROUTES.BACKTEST}><Button variant="primary">새 백테스트</Button></Link>
      </div>

      {history.isLoading && <Skeleton height={200} />}
      {history.isError && <ErrorCard message="백테스트 기록을 불러올 수 없습니다." />}

      {history.data && (
        <Card>
          <Card.Body className="p-0">
            <DataTable columns={columns} data={history.data} rowKey={(h) => h.job_id} pageSize={20} />
          </Card.Body>
        </Card>
      )}
    </>
  );
}
