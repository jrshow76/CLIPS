'use client';

import Link from 'next/link';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { DataTable, type Column } from '@/components/ui/table';
import { useTrades } from '@/lib/api/queries/trades';
import { ROUTES } from '@/lib/constants';
import { formatKST } from '@/lib/utils/date';
import { formatPct, pnlClass } from '@/lib/utils/format';
import type { MockTrade } from '@/lib/mocks/data';

export default function ReportTradesPage() {
  const [side, setSide] = useState<'ALL' | 'BUY' | 'SELL'>('ALL');
  const [q, setQ] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');

  const trades = useTrades({
    side: side === 'ALL' ? undefined : side,
    from: from || undefined,
    to: to || undefined,
  });

  const filtered = (trades.data ?? []).filter((t) =>
    q ? t.name.includes(q) || t.code.includes(q) : true,
  );

  const columns: Column<MockTrade>[] = [
    { key: 'ts', header: '거래 시각', sortAccessor: 'ts', cell: (t) => formatKST(t.ts) },
    {
      key: 'side',
      header: '구분',
      cell: (t) => <Badge variant={t.side === 'BUY' ? 'up' : 'down'}>{t.side === 'BUY' ? '매수' : '매도'}</Badge>,
    },
    {
      key: 'name',
      header: '종목',
      cell: (t) => (
        <Link href={ROUTES.CHART(t.code)} className="hover:underline">
          <span className="fw-semibold">{t.name}</span>
          <span className="text-xs text-subtle ml-2">{t.code}</span>
        </Link>
      ),
      sortAccessor: 'name',
    },
    { key: 'qty', header: '수량', align: 'right', cell: (t) => `${t.qty}주`, sortAccessor: 'qty' },
    { key: 'price', header: '가격', align: 'right', cell: (t) => t.price.toLocaleString('ko-KR'), sortAccessor: 'price' },
    { key: 'strategy_name', header: '전략', cell: (t) => t.strategy_name ?? '-' },
    {
      key: 'pnl',
      header: '손익',
      align: 'right',
      cell: (t) =>
        t.pnl != null ? <span className={pnlClass(t.pnl)}>{t.pnl.toLocaleString('ko-KR')}원</span> : '-',
    },
    {
      key: 'pnl_pct',
      header: '수익률',
      align: 'right',
      cell: (t) => (t.pnl_pct != null ? <span className={pnlClass(t.pnl_pct)}>{formatPct(t.pnl_pct)}</span> : '-'),
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>거래 내역</h1>
          <p>전체 거래 기록을 기간과 종목으로 필터링하여 조회합니다.</p>
        </div>
        <Link href={ROUTES.REPORT}><Button variant="outline">← 리포트</Button></Link>
      </div>

      <div className="filter-bar">
        <Input placeholder="종목명/코드" value={q} onChange={(e) => setQ(e.target.value)} />
        <Select value={side} onChange={(e) => setSide(e.target.value as typeof side)}>
          <option value="ALL">전체 구분</option>
          <option value="BUY">매수</option>
          <option value="SELL">매도</option>
        </Select>
        <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
      </div>

      <Card>
        <Card.Body className="p-0">
          {trades.isError && <div className="p-4"><ErrorCard message="거래 내역을 불러올 수 없습니다." /></div>}
          {trades.data && (
            <DataTable columns={columns} data={filtered} rowKey={(t) => t.id} pageSize={20} />
          )}
        </Card.Body>
      </Card>
    </>
  );
}
