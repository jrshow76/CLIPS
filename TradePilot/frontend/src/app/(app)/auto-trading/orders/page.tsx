'use client';

import Link from 'next/link';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Tabs } from '@/components/ui/tabs';
import { DataTable, type Column } from '@/components/ui/table';
import { useCancelOrder, useOrders } from '@/lib/api/queries/orders';
import { ROUTES } from '@/lib/constants';
import { formatKST } from '@/lib/utils/date';
import type { Order, OrderStatus } from '@/types/order';

type ModeFilter = 'ALL' | 'SIM' | 'LIVE';

const STATUS_LABEL: Record<OrderStatus, string> = {
  PENDING: '대기',
  ACCEPTED: '접수',
  PARTIAL: '부분체결',
  FILLED: '체결',
  CANCELED: '취소',
  REJECTED: '거부',
  EXPIRED: '만료',
};

export default function AutoTradingOrdersPage() {
  const [mode, setMode] = useState<ModeFilter>('ALL');
  const [status, setStatus] = useState<OrderStatus | 'ALL'>('ALL');
  const [q, setQ] = useState('');

  const orders = useOrders();
  const cancel = useCancelOrder();

  const filtered = (orders.data ?? []).filter((o) => {
    if (mode !== 'ALL' && o.mode !== mode) return false;
    if (status !== 'ALL' && o.status !== status) return false;
    if (q && !(o.code.includes(q) || (o.name ?? '').includes(q))) return false;
    return true;
  });

  const columns: Column<Order>[] = [
    { key: 'created_at', header: '시각', sortAccessor: 'created_at', cell: (o) => formatKST(o.created_at) },
    {
      key: 'mode',
      header: '모드',
      cell: (o) => <Badge variant={o.mode === 'LIVE' ? 'live' : 'sim'} dot>{o.mode}</Badge>,
    },
    {
      key: 'side',
      header: '구분',
      cell: (o) => <Badge variant={o.side === 'BUY' ? 'up' : 'down'}>{o.side === 'BUY' ? '매수' : '매도'}</Badge>,
    },
    {
      key: 'name',
      header: '종목',
      cell: (o) => (
        <Link href={ROUTES.CHART(o.code)} className="hover:underline">
          <span className="fw-semibold">{o.name ?? o.code}</span>
          <span className="text-xs text-subtle ml-2">{o.code}</span>
        </Link>
      ),
    },
    { key: 'order_type', header: '유형', cell: (o) => (o.order_type === 'MARKET' ? '시장가' : '지정가') },
    { key: 'qty', header: '수량', align: 'right', cell: (o) => `${o.qty}주`, sortAccessor: 'qty' },
    {
      key: 'price',
      header: '가격',
      align: 'right',
      cell: (o) => o.avg_fill_price?.toLocaleString('ko-KR') ?? o.price?.toLocaleString('ko-KR') ?? '-',
    },
    {
      key: 'status',
      header: '상태',
      cell: (o) => (
        <Badge
          variant={
            o.status === 'FILLED' ? 'success' : o.status === 'REJECTED' || o.status === 'CANCELED' ? 'danger' : 'info'
          }
        >
          {STATUS_LABEL[o.status]}
        </Badge>
      ),
    },
    {
      key: 'action',
      header: '',
      align: 'right',
      cell: (o) =>
        ['PENDING', 'ACCEPTED', 'PARTIAL'].includes(o.status) ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              if (window.confirm('주문을 취소하시겠습니까?')) cancel.mutate(o.id);
            }}
          >
            취소
          </Button>
        ) : null,
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>최근 주문 내역</h1>
          <p>시뮬/실거래 모드 모두 포함된 최근 주문 목록입니다.</p>
        </div>
        <Link href={ROUTES.AUTO_TRADING}><Button variant="outline">← 자동매매</Button></Link>
      </div>

      <Tabs
        value={mode}
        onChange={setMode}
        items={[
          { value: 'ALL', label: '전체' },
          { value: 'SIM', label: '시뮬' },
          { value: 'LIVE', label: '실거래' },
        ]}
      />

      <div className="filter-bar">
        <Input placeholder="종목명/코드" value={q} onChange={(e) => setQ(e.target.value)} />
        <Select value={status} onChange={(e) => setStatus(e.target.value as OrderStatus | 'ALL')}>
          <option value="ALL">전체 상태</option>
          <option value="ACCEPTED">접수</option>
          <option value="FILLED">체결</option>
          <option value="PARTIAL">부분체결</option>
          <option value="CANCELED">취소</option>
          <option value="REJECTED">거부</option>
        </Select>
      </div>

      <Card>
        <Card.Body className="p-0">
          {orders.isError && <div className="p-4"><ErrorCard message="주문 내역을 불러올 수 없습니다." /></div>}
          {orders.data && (
            <DataTable columns={columns} data={filtered} rowKey={(o) => o.id} pageSize={20} />
          )}
        </Card.Body>
      </Card>
    </>
  );
}
