'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Skeleton } from '@/components/ui/skeleton';
import { DataTable, type Column } from '@/components/ui/table';
import { useSectorFlow, useSectorRotation } from '@/lib/api/queries/market';
import { ROUTES } from '@/lib/constants';
import type { SectorRotation } from '@/types/sector-flow';

const SectorFlowChart = dynamic(() => import('../_components/sector-flow-chart').then((m) => m.SectorFlowChart), {
  ssr: false,
  loading: () => <Skeleton height={280} />,
});

export default function SectorFlowPage() {
  const flow = useSectorFlow();
  const rotation = useSectorRotation();

  const columns: Column<SectorRotation>[] = [
    { key: 'from_sector', header: '유출 섹터', cell: (r) => <Badge variant="down">{r.from_sector}</Badge> },
    { key: 'to_sector', header: '유입 섹터', cell: (r) => <Badge variant="up">{r.to_sector}</Badge> },
    {
      key: 'flow_value',
      header: '추정 자금',
      align: 'right',
      sortAccessor: 'flow_value',
      cell: (r) => `${r.flow_value.toLocaleString('ko-KR')}억`,
    },
    {
      key: 'intensity',
      header: '강도',
      align: 'right',
      sortAccessor: 'intensity',
      cell: (r) => (
        <div className="row items-center gap-2 justify-end">
          <div style={{ background: 'var(--color-bg-3)', width: 80, height: 6, borderRadius: 3 }}>
            <div style={{ background: 'var(--color-brand-500)', width: `${r.intensity * 100}%`, height: '100%', borderRadius: 3 }} />
          </div>
          <span className="text-xs text-subtle">{(r.intensity * 100).toFixed(0)}%</span>
        </div>
      ),
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>섹터 순환 분석</h1>
          <p>최근 자금흐름 및 섹터 간 자금 이동을 추적합니다.</p>
        </div>
        <Link href={ROUTES.SECTORS}><Button variant="outline">← 섹터 분석</Button></Link>
      </div>

      <Card className="mb-4">
        <Card.Header title="섹터별 누적 자금흐름" subtitle="최근 20거래일 기준" />
        <Card.Body>
          {flow.isError && <ErrorCard message="자금흐름 데이터를 불러올 수 없습니다." />}
          {flow.data && <SectorFlowChart data={flow.data} height={320} />}
          {flow.isLoading && <Skeleton height={280} />}
        </Card.Body>
      </Card>

      <Card>
        <Card.Header title="섹터 로테이션" subtitle="유출 → 유입 흐름" />
        <Card.Body className="p-0">
          {rotation.data && (
            <DataTable columns={columns} data={rotation.data} rowKey={(r) => `${r.from_sector}->${r.to_sector}`} />
          )}
        </Card.Body>
      </Card>
    </>
  );
}
