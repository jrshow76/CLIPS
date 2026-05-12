'use client';

import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Skeleton } from '@/components/ui/skeleton';
import { SectorHeatmap } from '@/components/charts/SectorHeatmap';
import { useSectors } from '@/lib/api/queries/sectors';

export default function SectorsPage() {
  const sectors = useSectors();
  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>업종분석</h1>
          <p>섹터별 등락률 히트맵과 주도주를 확인합니다.</p>
        </div>
      </div>

      <Card>
        <Card.Header title="섹터 히트맵" />
        <Card.Body>
          {sectors.isLoading && <Skeleton height={300} />}
          {sectors.isError && <ErrorCard message="섹터 데이터를 불러올 수 없습니다." />}
          {sectors.data && <SectorHeatmap sectors={sectors.data} />}
        </Card.Body>
      </Card>
    </>
  );
}
