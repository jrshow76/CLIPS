'use client';

import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs } from '@/components/ui/tabs';
import { IndicatorPanel } from '@/components/charts/IndicatorPanel';
import { useCandles, useQuote, useStockDetail } from '@/lib/api/queries/stocks';
import { cn } from '@/lib/utils/cn';
import { formatPct, pnlArrow, pnlClass } from '@/lib/utils/format';
import type { CandleInterval } from '@/types/stock';

// lightweight-charts는 SSR 불가 → 클라이언트 전용 로드
const CandlestickChart = dynamic(
  () => import('@/components/charts/CandlestickChart').then((m) => m.CandlestickChart),
  { ssr: false, loading: () => <Skeleton height={420} /> },
);

const INTERVALS: { value: CandleInterval; label: string }[] = [
  { value: '1m', label: '1분' },
  { value: '5m', label: '5분' },
  { value: '15m', label: '15분' },
  { value: '30m', label: '30분' },
  { value: 'D', label: '일' },
  { value: 'W', label: '주' },
  { value: 'M', label: '월' },
];

export default function ChartPage() {
  const params = useParams<{ code: string }>();
  const code = params?.code;
  const [interval, setInterval] = useState<CandleInterval>('D');
  const stock = useStockDetail(code);
  const quote = useQuote(code);
  const candles = useCandles(code, interval);

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <div className="row items-center gap-3">
            <h1>{stock.data?.name ?? code}</h1>
            <Badge variant="default">{code}</Badge>
            {stock.data?.sector && <span className="text-subtle text-sm">{stock.data.sector}</span>}
          </div>
          {quote.data && (
            <p className="text-sm mt-2">
              <span className="text-num text-strong fw-semibold text-20">
                {quote.data.price.toLocaleString('ko-KR')}
              </span>
              <span className={cn('ml-2', pnlClass(quote.data.change))}>
                {pnlArrow(quote.data.change)} {Math.abs(quote.data.change).toLocaleString('ko-KR')} ({formatPct(quote.data.change_pct)})
              </span>
            </p>
          )}
        </div>
        <div className="row gap-2">
          <Tabs
            variant="pill"
            value={interval}
            onChange={(v) => setInterval(v as CandleInterval)}
            items={INTERVALS}
          />
        </div>
      </div>

      <Card className="mb-4">
        <Card.Body className="p-3">
          {candles.isError && <ErrorCard message="캔들 데이터를 불러올 수 없습니다." />}
          {candles.data && <CandlestickChart data={candles.data} height={460} />}
          {candles.isLoading && <Skeleton height={420} />}
        </Card.Body>
      </Card>

      <div className="grid-cols-3">
        <Card>
          <Card.Header title="RSI(14)" />
          <Card.Body className="p-2">
            {candles.data ? <IndicatorPanel kind="RSI" candles={candles.data} /> : <Skeleton height={140} />}
          </Card.Body>
        </Card>
        <Card>
          <Card.Header title="MACD(12,26,9)" />
          <Card.Body className="p-2">
            {candles.data ? <IndicatorPanel kind="MACD" candles={candles.data} /> : <Skeleton height={140} />}
          </Card.Body>
        </Card>
        <Card>
          <Card.Header title="Stochastic(14)" />
          <Card.Body className="p-2">
            {candles.data ? <IndicatorPanel kind="STOCH" candles={candles.data} /> : <Skeleton height={140} />}
          </Card.Body>
        </Card>
      </div>

      <div className="row gap-2 mt-6">
        <Button variant="primary">매수</Button>
        <Button variant="danger">매도</Button>
        <Button variant="ghost">관심종목 추가</Button>
      </div>
    </>
  );
}
