'use client';

import { Sparkles, Target, TrendingDown } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Kpi } from '@/components/ui/kpi';
import { Skeleton } from '@/components/ui/skeleton';
import { StatRow } from '@/components/ui/stat-row';
import { OrderModal } from '@/components/orders/OrderModal';
import { useRecommendationDetail } from '@/lib/api/queries/recommendation-detail';
import { useQuote } from '@/lib/api/queries/stocks';
import { ROUTES } from '@/lib/constants';
import { cn } from '@/lib/utils/cn';
import { formatPct, pnlArrow, pnlClass } from '@/lib/utils/format';

export default function RecommendationDetailPage() {
  const params = useParams<{ id: string }>();
  const code = params?.id;
  const detail = useRecommendationDetail(code);
  const quote = useQuote(code);
  const [orderOpen, setOrderOpen] = useState(false);

  if (detail.isLoading) return <Skeleton height={400} />;
  if (detail.isError || !detail.data || !code) {
    return <ErrorCard message="추천 정보를 불러올 수 없습니다." />;
  }
  const d = detail.data;

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <div className="row items-center gap-3">
            <h1>{d.name}</h1>
            <Badge variant="default">{d.code}</Badge>
            {d.sector && <span className="text-subtle text-sm">{d.sector}</span>}
            <Badge variant="success">AI 점수 {d.score}</Badge>
          </div>
          <p className="text-sm mt-2">
            <span className="text-num text-strong fw-semibold text-20">
              {(quote.data?.price ?? d.price).toLocaleString('ko-KR')}
            </span>
            <span className={cn('ml-2', pnlClass(d.change_pct))}>
              {pnlArrow(d.change_pct)} {formatPct(Math.abs(d.change_pct))}
            </span>
          </p>
        </div>
        <div className="row gap-2">
          <Link href={ROUTES.CHART(d.code)}>
            <Button variant="outline">차트 보기</Button>
          </Link>
          <Button variant="primary" onClick={() => setOrderOpen(true)}>
            매수 주문
          </Button>
        </div>
      </div>

      {/* AI 코멘트 */}
      <Card className="mb-4">
        <Card.Body>
          <div className="row gap-3 items-start">
            <Sparkles className="text-brand h-5 w-5 mt-1 flex-none" />
            <div>
              <p className="text-strong fw-semibold mb-1">AI 분석 코멘트</p>
              <p className="text-sm text-muted">{d.ai_comment}</p>
            </div>
          </div>
        </Card.Body>
      </Card>

      {/* 추천 사유 + 지표 + 목표/손절 */}
      <div className="grid-cols-3">
        <Card>
          <Card.Header title="추천 사유" />
          <Card.Body className="stack gap-3">
            {d.reasons.map((r) => (
              <div key={r.label} className="stack gap-1">
                <Badge variant="info">{r.label}</Badge>
                <p className="text-sm">{r.detail}</p>
              </div>
            ))}
          </Card.Body>
        </Card>

        <Card>
          <Card.Header title="핵심 지표" />
          <Card.Body className="stack gap-2">
            <StatRow label="RSI(14)" value={<span className="text-num">{d.indicators.rsi.toFixed(1)}</span>} />
            <StatRow label="5일선" value={<span className="text-num">{d.indicators.ma5.toLocaleString('ko-KR')}</span>} />
            <StatRow label="20일선" value={<span className="text-num">{d.indicators.ma20.toLocaleString('ko-KR')}</span>} />
            <StatRow label="MACD" value={<span className="text-num">{d.indicators.macd.toFixed(2)}</span>} />
            <StatRow label="거래량(전일 대비)" value={<span className="text-num">{d.indicators.volume_ratio.toFixed(2)}배</span>} />
          </Card.Body>
        </Card>

        <Card>
          <Card.Header title="가격 가이드" />
          <Card.Body className="stack gap-3">
            <Kpi
              label={<span className="row items-center gap-1"><Target className="h-4 w-4" /> 목표가</span>}
              value={<span className="text-up text-num">{d.target_price.toLocaleString('ko-KR')}</span>}
              delta={<span className="text-subtle text-xs">현재가 대비 +{(((d.target_price - d.price) / d.price) * 100).toFixed(1)}%</span>}
            />
            <div className="divider" />
            <Kpi
              label={<span className="row items-center gap-1"><TrendingDown className="h-4 w-4" /> 손절가</span>}
              value={<span className="text-down text-num">{d.stop_price.toLocaleString('ko-KR')}</span>}
              delta={<span className="text-subtle text-xs">현재가 대비 {(((d.stop_price - d.price) / d.price) * 100).toFixed(1)}%</span>}
            />
          </Card.Body>
        </Card>
      </div>

      <OrderModal
        open={orderOpen}
        onClose={() => setOrderOpen(false)}
        code={d.code}
        name={d.name}
        defaultSide="BUY"
        suggestedPrice={d.price}
      />
    </>
  );
}
