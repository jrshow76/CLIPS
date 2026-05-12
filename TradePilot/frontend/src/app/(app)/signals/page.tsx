'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { ErrorCard } from '@/components/ui/error-card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Tabs } from '@/components/ui/tabs';
import { DataTable, type Column } from '@/components/ui/table';
import { useSignals } from '@/lib/api/queries/signals';
import { ROUTES } from '@/lib/constants';
import { formatKSTTime } from '@/lib/utils/date';
import { toast } from '@/stores/notification-store';
import type { Signal, SignalAction } from '@/types/signal';

type StatusTab = 'ALL' | 'ACTIVE' | 'CONSUMED' | 'EXPIRED';
type FilterAction = 'ALL' | SignalAction;

export default function SignalsPage() {
  const router = useRouter();
  const [statusTab, setStatusTab] = useState<StatusTab>('ALL');
  const [action, setAction] = useState<FilterAction>('ALL');
  const [q, setQ] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const signals = useSignals(action === 'ALL' ? undefined : { action: action as 'BUY' | 'SELL' });

  const filtered = (signals.data ?? []).filter((s) => {
    if (q && !(s.name.includes(q) || s.code.includes(q))) return false;
    if (statusTab === 'ACTIVE' && s.consumed) return false;
    if (statusTab === 'CONSUMED' && !s.consumed) return false;
    return true;
  });

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  function toggleAll() {
    if (selected.size === filtered.length) setSelected(new Set());
    else setSelected(new Set(filtered.map((s) => s.id)));
  }

  const columns: Column<Signal>[] = [
    {
      key: 'select',
      header: <Checkbox checked={selected.size > 0 && selected.size === filtered.length} onChange={toggleAll} />,
      width: 40,
      cell: (s) => <Checkbox checked={selected.has(s.id)} onChange={() => toggle(s.id)} />,
    },
    { key: 'time', header: '시각', sortAccessor: 'created_at', cell: (s) => formatKSTTime(s.created_at) },
    {
      key: 'action',
      header: '구분',
      cell: (s) => (
        <Badge variant={s.action === 'BUY' ? 'up' : s.action === 'SELL' ? 'down' : 'default'}>
          {s.action === 'BUY' ? '매수' : s.action === 'SELL' ? '매도' : '관망'}
        </Badge>
      ),
    },
    {
      key: 'name',
      header: '종목',
      cell: (s) => (
        <Link href={ROUTES.SIGNAL_DETAIL(s.id)} className="hover:underline">
          <span className="fw-semibold">{s.name}</span>
          <span className="text-xs text-subtle ml-2">{s.code}</span>
        </Link>
      ),
      sortAccessor: 'name',
    },
    { key: 'source', header: '사유', cell: (s) => s.strategy_name ?? s.source },
    { key: 'price', header: '현재가', align: 'right', cell: (s) => s.price.toLocaleString('ko-KR'), sortAccessor: 'price' },
    { key: 'confidence', header: '신뢰도', align: 'right', cell: (s) => `${s.confidence}%`, sortAccessor: 'confidence' },
    {
      key: 'action_btn',
      header: '',
      align: 'right',
      cell: (s) => (
        <Button variant="primary" size="sm" onClick={() => router.push(ROUTES.SIGNAL_DETAIL(s.id))}>
          상세
        </Button>
      ),
    },
  ];

  function bulkConsume() {
    toast.success(`${selected.size}건의 시그널을 처리했습니다.`);
    setSelected(new Set());
  }

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>매매 시그널</h1>
          <p>활성 전략이 생성한 매수/매도 시그널입니다.</p>
        </div>
        <Link href={ROUTES.SIGNAL_RULES}>
          <Button variant="outline">알림 규칙 관리</Button>
        </Link>
      </div>

      <Tabs
        value={statusTab}
        onChange={setStatusTab}
        items={[
          { value: 'ALL', label: '전체' },
          { value: 'ACTIVE', label: '활성' },
          { value: 'CONSUMED', label: '완료' },
          { value: 'EXPIRED', label: '만료' },
        ]}
      />

      <div className="filter-bar">
        <Input placeholder="종목명 또는 코드" value={q} onChange={(e) => setQ(e.target.value)} />
        <Select value={action} onChange={(e) => setAction(e.target.value as FilterAction)}>
          <option value="ALL">전체 구분</option>
          <option value="BUY">매수</option>
          <option value="SELL">매도</option>
        </Select>
        {selected.size > 0 && (
          <Button variant="primary" onClick={bulkConsume}>
            선택 {selected.size}건 처리
          </Button>
        )}
      </div>

      <Card>
        <Card.Body className="p-0">
          {signals.isError && (
            <div className="p-4">
              <ErrorCard message="시그널을 불러올 수 없습니다." />
            </div>
          )}
          {signals.data && (
            <DataTable
              columns={columns}
              data={filtered}
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
