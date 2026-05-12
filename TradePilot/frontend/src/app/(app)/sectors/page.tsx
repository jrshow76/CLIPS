'use client';

import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Skeleton } from '@/components/ui/skeleton';
import { DataTable, type Column } from '@/components/ui/table';
import { SectorHeatmap } from '@/components/charts/SectorHeatmap';
import { useSectors } from '@/lib/api/queries/sectors';
import { useSectorFlow } from '@/lib/api/queries/market';
import { ROUTES } from '@/lib/constants';
import { formatPct, pnlClass } from '@/lib/utils/format';
import type { Sector } from '@/types/recommendation';

const SectorFlowChart = dynamic(() => import('./_components/sector-flow-chart').then((m) => m.SectorFlowChart), {
  ssr: false,
  loading: () => <Skeleton height={260} />,
});

export default function SectorsPage() {
  const router = useRouter();
  const sectors = useSectors();
  const flow = useSectorFlow();

  const columns: Column<Sector>[] = [
    { key: 'name', header: '섹터', cell: (s) => <span className="fw-semibold">{s.name}</span>, sortAccessor: 'name' },
    {
      key: 'change_pct',
      header: '등락률',
      align: 'right',
      sortAccessor: 'change_pct',
      cell: (s) => <span className={pnlClass(s.change_pct)}>{formatPct(s.change_pct)}</span>,
    },
    {
      key: 'action',
      header: '',
      align: 'right',
      cell: (s) => (
        <Button variant="outline" size="sm" onClick={() => router.push(ROUTES.SECTOR_DETAIL(s.code))}>
          구성종목 →
        </Button>
      ),
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>업종분석</h1>
          <p>섹터별 등락률 히트맵과 자금흐름을 확인합니다.</p>
        </div>
        <div className="row gap-2">
          <Button variant="outline" onClick={() => router.push(ROUTES.SECTOR_FLOW)}>
            순환 분석 →
          </Button>
        </div>
      </div>

      <Card className="mb-4">
        <Card.Header title="섹터 히트맵" subtitle="셀 클릭 시 해당 섹터 상세로 이동" />
        <Card.Body>
          {sectors.isLoading && <Skeleton height={300} />}
          {sectors.isError && <ErrorCard message="섹터 데이터를 불러올 수 없습니다." />}
          {sectors.data && (
            <SectorHeatmap
              sectors={sectors.data}
              onSelect={(code) => router.push(ROUTES.SECTOR_DETAIL(code))}
            />
          )}
        </Card.Body>
      </Card>

      <div className="grid-cols-2">
        <Card>
          <Card.Header title="섹터 자금흐름 (최근 20일)" right={<Badge variant="info">억 원</Badge>} />
          <Card.Body>
            {flow.isLoading && <Skeleton height={260} />}
            {flow.isError && <ErrorCard message="자금흐름 데이터를 불러올 수 없습니다." />}
            {flow.data && <SectorFlowChart data={flow.data} />}
          </Card.Body>
        </Card>

        <Card>
          <Card.Header title="등락률 표" />
          <Card.Body className="p-0">
            {sectors.data && (
              <DataTable
                columns={columns}
                data={sectors.data}
                rowKey={(s) => s.code}
                pageSize={10}
              />
            )}
          </Card.Body>
        </Card>
      </div>
    </>
  );
}
