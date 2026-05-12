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
 * 추천주 페이지 (강화).
 * - 좌측 필터 사이드 패널 + 우측 테이블.
 * - 섹터/시가총액/점수/검색어 결합 필터.
 */
const SECTORS = ['반도체', '제약', '화학', '자동차', '2차전지', '인터넷', '철강', '금융', '전기·전자', '게임'];

type CapBucket = 'ALL' | 'LARGE' | 'MID' | 'SMALL';

export default function RecommendationsPage() {
  const [sector, setSector] = useState<string>('');
  const [minScore, setMinScore] = useState<number>(0);
  const [cap, setCap] = useState<CapBucket>('ALL');
  const [reason, setReason] = useState<string>('');
  const [q, setQ] = useState('');

  const reco = useRecommendations({
    sector: sector || undefined,
    min_score: minScore || undefined,
  });

  const filtered = (reco.data ?? []).filter((r) => {
    if (q && !(r.name.includes(q) || r.code.includes(q))) return false;
    if (reason && r.reason !== reason) return false;
    if (cap !== 'ALL') {
      // 데모: 단순 점수 기반 버킷 분류
      if (cap === 'LARGE' && r.score < 85) return false;
      if (cap === 'MID' && (r.score < 75 || r.score >= 85)) return false;
      if (cap === 'SMALL' && r.score >= 75) return false;
    }
    return true;
  });

  const columns: Column<Recommendation>[] = [
    {
      key: 'name',
      header: '종목',
      cell: (r) => (
        <Link href={ROUTES.RECOMMENDATION_DETAIL(r.code)} className="hover:underline">
          <div className="fw-semibold">{r.name}</div>
          <div className="text-xs text-subtle">{r.code} · {r.sector ?? '-'}</div>
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
        <div className="row gap-1 justify-end">
          <Link href={ROUTES.CHART(r.code)}>
            <Button variant="outline" size="sm">차트</Button>
          </Link>
          <Link href={ROUTES.RECOMMENDATION_DETAIL(r.code)}>
            <Button variant="primary" size="sm">상세</Button>
          </Link>
        </div>
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
        <div className="row gap-2">
          <Button variant="outline" size="sm" onClick={() => reco.refetch()}>새로고침</Button>
        </div>
      </div>

      <div
        className="grid"
        style={{ gridTemplateColumns: '260px 1fr', gap: 'var(--space-4)', alignItems: 'flex-start' }}
        data-grid="reco-layout"
      >
        {/* 필터 사이드 패널 */}
        <Card>
          <Card.Header title="필터" />
          <Card.Body className="stack gap-4">
            <div className="stack gap-2">
              <label className="field__label">검색</label>
              <Input
                placeholder="종목명/코드"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
            <div className="stack gap-2">
              <label className="field__label">섹터</label>
              <Select value={sector} onChange={(e) => setSector(e.target.value)}>
                <option value="">전체</option>
                {SECTORS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </Select>
            </div>
            <div className="stack gap-2">
              <label className="field__label">시가총액</label>
              <Select value={cap} onChange={(e) => setCap(e.target.value as CapBucket)}>
                <option value="ALL">전체</option>
                <option value="LARGE">대형주</option>
                <option value="MID">중형주</option>
                <option value="SMALL">소형주</option>
              </Select>
            </div>
            <div className="stack gap-2">
              <label className="field__label">최소 점수</label>
              <Select value={minScore} onChange={(e) => setMinScore(Number(e.target.value))}>
                <option value={0}>전체</option>
                <option value={70}>70+</option>
                <option value={80}>80+</option>
                <option value={90}>90+</option>
              </Select>
            </div>
            <div className="stack gap-2">
              <label className="field__label">추천 사유</label>
              <Select value={reason} onChange={(e) => setReason(e.target.value)}>
                <option value="">전체</option>
                <option value="RSI_OVERSOLD">RSI 과매도</option>
                <option value="GOLDEN_CROSS">골든크로스</option>
                <option value="VOLUME_SURGE">거래량 급증</option>
                <option value="MACD_TURN">MACD 전환</option>
                <option value="BOLLINGER_LOWER">볼린저 하단</option>
              </Select>
            </div>

            <Button
              variant="ghost"
              onClick={() => {
                setSector('');
                setMinScore(0);
                setCap('ALL');
                setReason('');
                setQ('');
              }}
            >
              필터 초기화
            </Button>
          </Card.Body>
        </Card>

        <Card>
          <Card.Header
            title={`결과 ${filtered.length}건`}
            right={<span className="text-subtle text-xs">점수/등락률 헤더 클릭으로 정렬</span>}
          />
          <Card.Body className="p-0">
            {reco.isLoading && <div className="p-4"><SkeletonRows /></div>}
            {reco.isError && (
              <div className="p-4">
                <ErrorCard
                  message="추천주 데이터를 불러올 수 없습니다."
                  action={<Button onClick={() => reco.refetch()}>다시 시도</Button>}
                />
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
      </div>

      <style jsx>{`
        @media (max-width: 1024px) {
          div[data-grid='reco-layout'] { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </>
  );
}
