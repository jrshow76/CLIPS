'use client';

import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Tabs } from '@/components/ui/tabs';
import { DataTable, type Column } from '@/components/ui/table';
import { useSignals } from '@/lib/api/queries/signals';
import { formatKSTTime } from '@/lib/utils/date';
import type { Signal, SignalAction } from '@/types/signal';

type FilterAction = 'ALL' | SignalAction;

export default function SignalsPage() {
  const [filter, setFilter] = useState<FilterAction>('ALL');
  const signals = useSignals(filter === 'ALL' ? undefined : { action: filter as 'BUY' | 'SELL' });

  const columns: Column<Signal>[] = [
    {
      key: 'time',
      header: '시각',
      sortAccessor: 'created_at',
      cell: (s) => formatKSTTime(s.created_at),
    },
    {
      key: 'action',
      header: '구분',
      cell: (s) => (
        <Badge variant={s.action === 'BUY' ? 'up' : s.action === 'SELL' ? 'down' : 'default'}>
          {s.action === 'BUY' ? '매수' : s.action === 'SELL' ? '매도' : '관망'}
        </Badge>
      ),
    },
    { key: 'name', header: '종목', cell: (s) => `${s.name} (${s.code})`, sortAccessor: 'name' },
    { key: 'source', header: '사유', cell: (s) => s.strategy_name ?? s.source },
    {
      key: 'price',
      header: '현재가',
      align: 'right',
      cell: (s) => s.price.toLocaleString('ko-KR'),
      sortAccessor: 'price',
    },
    {
      key: 'confidence',
      header: '신뢰도',
      align: 'right',
      cell: (s) => `${s.confidence}%`,
      sortAccessor: 'confidence',
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>매매 시그널</h1>
          <p>활성 전략이 생성한 매수/매도 시그널입니다.</p>
        </div>
      </div>

      <Tabs
        value={filter}
        onChange={setFilter}
        items={[
          { value: 'ALL', label: '전체' },
          { value: 'BUY', label: '매수' },
          { value: 'SELL', label: '매도' },
        ]}
      />

      <Card>
        <Card.Body className="p-0">
          {signals.isError && <div className="p-4"><ErrorCard message="시그널을 불러올 수 없습니다." /></div>}
          {signals.data && (
            <DataTable
              columns={columns}
              data={signals.data}
              rowKey={(s) => s.id}
              pageSize={20}
              emptyMessage="현재 시그널이 없습니다."
            />
          )}
        </Card.Body>
      </Card>
    </>
  );
}
