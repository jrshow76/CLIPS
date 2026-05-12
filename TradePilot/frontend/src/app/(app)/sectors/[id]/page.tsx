'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Kpi } from '@/components/ui/kpi';
import { Skeleton } from '@/components/ui/skeleton';
import { DataTable, type Column } from '@/components/ui/table';
import { useSectors } from '@/lib/api/queries/sectors';
import { useRecommendations } from '@/lib/api/queries/recommendations';
import { ROUTES } from '@/lib/constants';
import { formatPct, pnlClass } from '@/lib/utils/format';
import type { Recommendation } from '@/types/recommendation';

/**
 * 섹터 상세: 등락률 KPI + 구성종목(추천 데이터 재활용) + 차트 이동.
 * - 실제 API: /sectors/:code + /sectors/:code/stocks
 * - 데모: 추천 데이터 중 sector 일치 종목으로 대체.
 */
export default function SectorDetailPage() {
  const params = useParams<{ id: string }>();
  const code = params?.id;
  const sectors = useSectors();
  const sector = sectors.data?.find((s) => s.code === code);
  const recos = useRecommendations({ sector: sector?.name });

  if (sectors.isLoading) return <Skeleton height={300} />;
  if (sectors.isError || !sector) {
    return (
      <ErrorCard
        message={`섹터(${code})를 찾을 수 없습니다.`}
        action={<Link href={ROUTES.SECTORS}><Button variant="primary">섹터 목록으로</Button></Link>}
      />
    );
  }

  const columns: Column<Recommendation>[] = [
    {
      key: 'name',
      header: '종목',
      cell: (r) => (
        <Link href={ROUTES.CHART(r.code)} className="hover:underline">
          <div className="fw-semibold">{r.name}</div>
          <div className="text-xs text-subtle">{r.code}</div>
        </Link>
      ),
      sortAccessor: 'name',
    },
    { key: 'reason_text', header: '특징', cell: (r) => r.reason_text },
    {
      key: 'price',
      header: '현재가',
      align: 'right',
      sortAccessor: 'price',
      cell: (r) => r.price.toLocaleString('ko-KR'),
    },
    {
      key: 'change_pct',
      header: '등락률',
      align: 'right',
      sortAccessor: 'change_pct',
      cell: (r) => <span className={pnlClass(r.change_pct)}>{formatPct(r.change_pct)}</span>,
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <div className="row items-center gap-3">
            <h1>{sector.name}</h1>
            <Badge variant="default">{sector.code}</Badge>
          </div>
          <p className={`text-sm mt-1 ${pnlClass(sector.change_pct)}`}>오늘 {formatPct(sector.change_pct)}</p>
        </div>
        <Link href={ROUTES.SECTORS}><Button variant="outline">← 섹터 목록</Button></Link>
      </div>

      <section className="grid-cols-4 mb-4">
        <Card><Card.Body><Kpi label="섹터 등락률" value={<span className={pnlClass(sector.change_pct)}>{formatPct(sector.change_pct)}</span>} /></Card.Body></Card>
        <Card><Card.Body><Kpi label="구성 종목 수" value={`${recos.data?.length ?? '-'}개`} /></Card.Body></Card>
        <Card><Card.Body><Kpi label="시가총액" value={sector.market_cap ? `${(sector.market_cap / 1e12).toFixed(1)}조` : '-'} /></Card.Body></Card>
        <Card><Card.Body><Kpi label="주도주" value={sector.top_stocks?.[0]?.name ?? '-'} /></Card.Body></Card>
      </section>

      <Card>
        <Card.Header title="구성 종목" subtitle="추천 점수 기준 상위 표시" />
        <Card.Body className="p-0">
          {recos.data && recos.data.length === 0 && (
            <p className="text-subtle p-4 center">표시할 종목이 없습니다. 다른 섹터를 확인해보세요.</p>
          )}
          {recos.data && recos.data.length > 0 && (
            <DataTable columns={columns} data={recos.data} rowKey={(r) => r.code} pageSize={20} />
          )}
        </Card.Body>
      </Card>
    </>
  );
}
