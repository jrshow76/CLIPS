'use client';

import Link from 'next/link';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { SkeletonRows } from '@/components/ui/skeleton';
import { DataTable, type Column } from '@/components/ui/table';
import { useRecommendations } from '@/lib/api/queries/recommendations';
import { ROUTES } from '@/lib/constants';
import { formatPct, pnlClass } from '@/lib/utils/format';
import type { Recommendation } from '@/types/recommendation';

/**
 * 추천주 페이지.
 * FrontendDev 가이드:
 *  - 상세는 /recommendations/[code]에 별도 page.tsx 추가.
 *  - 필터(sector, min_score)는 URL searchParams로 동기화 검토.
 */
export default function RecommendationsPage() {
  const [sector, setSector] = useState<string>('');
  const [minScore, setMinScore] = useState<number>(0);
  const [q, setQ] = useState('');
  const reco = useRecommendations({
    sector: sector || undefined,
    min_score: minScore || undefined,
  });

  const filtered = (reco.data ?? []).filter((r) => (q ? r.name.includes(q) || r.code.includes(q) : true));

  const columns: Column<Recommendation>[] = [
    {
      key: 'name',
      header: '종목',
      cell: (r) => (
        <Link href={ROUTES.CHART(r.code)} className="hover:underline">
          <div className="fw-semibold">{r.name}</div>
          <div className="text-xs text-subtle">
            {r.code} · {r.sector ?? '-'}
          </div>
        </Link>
      ),
      sortAccessor: 'name',
    },
    { key: 'reason', header: '추천 사유', cell: (r) => r.reason_text },
    {
      key: 'score',
      header: '점수',
      align: 'right',
      sortAccessor: 'score',
      cell: (r) => <Badge variant="success">{r.score}</Badge>,
    },
    {
      key: 'price',
      header: '현재가',
      align: 'right',
      sortAccessor: 'price',
      cell: (r) => r.price.toLocaleString('ko-KR'),
    },
    {
      key: 'change',
      header: '등락률',
      align: 'right',
      sortAccessor: 'change_pct',
      cell: (r) => <span className={pnlClass(r.change_pct)}>{formatPct(r.change_pct)}</span>,
    },
    {
      key: 'action',
      header: '',
      align: 'right',
      cell: (r) => (
        <Link href={ROUTES.CHART(r.code)}>
          <Button variant="outline" size="sm">
            차트
          </Button>
        </Link>
      ),
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>추천주</h1>
          <p>AI 점수 + 기술적 지표 기반 추천 종목 리스트입니다.</p>
        </div>
      </div>

      <div className="filter-bar">
        <Input placeholder="종목명 또는 코드" value={q} onChange={(e) => setQ(e.target.value)} />
        <Select value={sector} onChange={(e) => setSector(e.target.value)}>
          <option value="">전체 섹터</option>
          <option value="반도체">반도체</option>
          <option value="제약">제약</option>
          <option value="화학">화학</option>
          <option value="자동차">자동차</option>
          <option value="2차전지">2차전지</option>
        </Select>
        <Select value={minScore} onChange={(e) => setMinScore(Number(e.target.value))}>
          <option value={0}>점수 전체</option>
          <option value={70}>70+</option>
          <option value={80}>80+</option>
          <option value={90}>90+</option>
        </Select>
      </div>

      <Card>
        <Card.Body className="p-0">
          {reco.isLoading && <div className="p-4"><SkeletonRows /></div>}
          {reco.isError && (
            <div className="p-4">
              <ErrorCard message="추천주 데이터를 불러올 수 없습니다." action={<Button onClick={() => reco.refetch()}>다시 시도</Button>} />
            </div>
          )}
          {reco.data && (
            <DataTable
              columns={columns}
              data={filtered}
              rowKey={(r) => r.code}
              pageSize={20}
              emptyMessage="조건에 맞는 추천 종목이 없습니다."
            />
          )}
        </Card.Body>
      </Card>
    </>
  );
}
