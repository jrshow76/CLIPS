'use client';

import dynamic from 'next/dynamic';
import { useParams, useRouter } from 'next/navigation';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { ErrorCard } from '@/components/ui/error-card';
import { Field, Input } from '@/components/ui/input';
import { RadioGroup } from '@/components/ui/radio';
import { RealtimeIndicator } from '@/components/ui/realtime-indicator';
import { Skeleton } from '@/components/ui/skeleton';
import { StatRow } from '@/components/ui/stat-row';
import { Tabs } from '@/components/ui/tabs';
import { IndicatorPanel } from '@/components/charts/IndicatorPanel';
import { StockSearchInput } from '@/components/forms/StockSearchInput';
import { OrderBook } from '@/components/orderbook/OrderBook';
import { OrderModal } from '@/components/orders/OrderModal';
import { useRealtimeTick } from '@/hooks/useRealtimeTick';
import { useCandles, useQuote, useStockDetail } from '@/lib/api/queries/stocks';
import { ROUTES } from '@/lib/constants';
import { cn } from '@/lib/utils/cn';
import { formatPct, pnlArrow, pnlClass } from '@/lib/utils/format';
import type { OrderSide } from '@/types/order';
import type { CandleInterval } from '@/types/stock';

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

type Indicators = { rsi: boolean; macd: boolean; stoch: boolean; bbands: boolean };

export default function ChartPage() {
  const router = useRouter();
  const params = useParams<{ code: string }>();
  const code = params?.code;
  const [interval, setInterval] = useState<CandleInterval>('D');
  const [indicators, setIndicators] = useState<Indicators>({ rsi: true, macd: true, stoch: false, bbands: false });
  const [orderOpen, setOrderOpen] = useState(false);
  const [orderSide, setOrderSide] = useState<OrderSide>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('LIMIT');
  const [qty, setQty] = useState<number>(1);
  const [price, setPrice] = useState<number>(0);

  const stock = useStockDetail(code);
  const quote = useQuote(code);
  const candles = useCandles(code, interval);
  // 종목 페이지 진입 시 실시간 시세 자동 구독 (LIVE 가격/뱃지 표시)
  const live = useRealtimeTick(code);
  const livePrice = live.price ?? quote.data?.price;
  const liveChange = live.price != null ? live.change : (quote.data?.change ?? 0);
  const liveChangePct = live.price != null ? live.changePct : (quote.data?.change_pct ?? 0);

  function onSelectFromSearch(s: { code: string; name: string }) {
    router.push(ROUTES.CHART(s.code));
  }

  function openOrder(side: OrderSide) {
    setOrderSide(side);
    setPrice(quote.data?.price ?? 0);
    setOrderOpen(true);
  }

  function submitQuick() {
    setPrice((p) => (p > 0 ? p : quote.data?.price ?? 0));
    setOrderOpen(true);
  }

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <div className="row items-center gap-3">
            <h1>{stock.data?.name ?? code}</h1>
            <Badge variant="default">{code}</Badge>
            {stock.data?.sector && <span className="text-subtle text-sm">{stock.data.sector}</span>}
            {live.isLive && <Badge variant="success" dot>LIVE</Badge>}
            <RealtimeIndicator showLabel={false} />
          </div>
          {(livePrice != null) && (
            <p className="text-sm mt-2">
              <span className="text-num text-strong fw-semibold text-20">
                {livePrice.toLocaleString('ko-KR')}
              </span>
              <span className={cn('ml-2', pnlClass(liveChange))}>
                {pnlArrow(liveChange)} {Math.abs(liveChange).toLocaleString('ko-KR')} ({formatPct(liveChangePct)})
              </span>
            </p>
          )}
        </div>
        <div className="row gap-2" style={{ minWidth: 280 }}>
          <StockSearchInput onSelect={onSelectFromSearch} placeholder="다른 종목 검색" />
        </div>
      </div>

      <div
        className="grid"
        style={{ gridTemplateColumns: '1fr 260px 320px', gap: 'var(--space-4)', alignItems: 'flex-start' }}
        data-grid="chart-layout"
      >
        {/* ===== 좌측: 차트 + 지표 ===== */}
        <div className="stack gap-4">
          <Card>
            <Card.Header
              title="가격 차트"
              right={
                <Tabs
                  variant="pill"
                  value={interval}
                  onChange={(v) => setInterval(v as CandleInterval)}
                  items={INTERVALS}
                />
              }
            />
            <Card.Body className="p-3">
              {candles.isError && <ErrorCard message="캔들 데이터를 불러올 수 없습니다." />}
              {candles.data && (
                <CandlestickChart
                  data={candles.data}
                  height={460}
                  realtime
                  stockCode={code}
                />
              )}
              {candles.isLoading && <Skeleton height={420} />}
            </Card.Body>
          </Card>

          {/* 지표 토글 */}
          <Card>
            <Card.Header title="기술 지표" />
            <Card.Body>
              <div className="row gap-4 flex-wrap mb-3">
                <Checkbox checked={indicators.rsi} onChange={(v) => setIndicators((s) => ({ ...s, rsi: v }))} label="RSI(14)" />
                <Checkbox checked={indicators.macd} onChange={(v) => setIndicators((s) => ({ ...s, macd: v }))} label="MACD(12,26,9)" />
                <Checkbox checked={indicators.stoch} onChange={(v) => setIndicators((s) => ({ ...s, stoch: v }))} label="Stochastic(14)" />
                <Checkbox checked={indicators.bbands} onChange={(v) => setIndicators((s) => ({ ...s, bbands: v }))} label="볼린저밴드" />
              </div>
              <div className="grid-cols-3">
                {indicators.rsi && (
                  <Card><Card.Header title="RSI(14)" /><Card.Body className="p-2">
                    {candles.data ? <IndicatorPanel kind="RSI" candles={candles.data} /> : <Skeleton height={140} />}
                  </Card.Body></Card>
                )}
                {indicators.macd && (
                  <Card><Card.Header title="MACD(12,26,9)" /><Card.Body className="p-2">
                    {candles.data ? <IndicatorPanel kind="MACD" candles={candles.data} /> : <Skeleton height={140} />}
                  </Card.Body></Card>
                )}
                {indicators.stoch && (
                  <Card><Card.Header title="Stochastic(14)" /><Card.Body className="p-2">
                    {candles.data ? <IndicatorPanel kind="STOCH" candles={candles.data} /> : <Skeleton height={140} />}
                  </Card.Body></Card>
                )}
              </div>
            </Card.Body>
          </Card>
        </div>

        {/* ===== 중앙: 호가창 (Level 2) ===== */}
        <Card data-area="orderbook">
          <Card.Header
            title="호가창"
            subtitle="가격 클릭 시 주문에 적용"
          />
          <Card.Body className="p-0">
            <OrderBook
              stockCode={code}
              onPriceClick={(p) => {
                setPrice(p);
              }}
            />
          </Card.Body>
        </Card>

        {/* ===== 우측: 빠른 주문 패널 ===== */}
        <Card>
          <Card.Header title="빠른 주문" />
          <Card.Body className="stack gap-4">
            <Field label="구분">
              <RadioGroup<OrderSide>
                name="side"
                value={orderSide}
                onChange={setOrderSide}
                options={[
                  { value: 'BUY', label: '매수' },
                  { value: 'SELL', label: '매도' },
                ]}
              />
            </Field>
            <Field label="주문 유형">
              <RadioGroup<'MARKET' | 'LIMIT'>
                name="orderType"
                value={orderType}
                onChange={setOrderType}
                options={[
                  { value: 'LIMIT', label: '지정가' },
                  { value: 'MARKET', label: '시장가' },
                ]}
              />
            </Field>
            <Field label="수량 (주)">
              <Input
                type="number"
                min={1}
                value={qty}
                onChange={(e) => setQty(Number(e.target.value))}
              />
            </Field>
            {orderType === 'LIMIT' && (
              <Field label="지정가 (원)">
                <Input
                  type="number"
                  min={0}
                  placeholder={quote.data ? String(quote.data.price) : ''}
                  value={price || ''}
                  onChange={(e) => setPrice(Number(e.target.value))}
                />
              </Field>
            )}
            <StatRow
              label="예상 체결금액"
              value={
                <span className="fw-semibold text-num">
                  {(((orderType === 'LIMIT' ? price : quote.data?.price ?? 0) * qty) || 0).toLocaleString('ko-KR')}원
                </span>
              }
            />
            <div className="row gap-2">
              <Button variant="primary" block onClick={() => { setOrderSide('BUY'); submitQuick(); }}>매수</Button>
              <Button variant="danger" block onClick={() => { setOrderSide('SELL'); submitQuick(); }}>매도</Button>
            </div>
            <div className="divider" />
            <Button variant="ghost" block onClick={() => openOrder('BUY')}>
              상세 주문창 열기
            </Button>
          </Card.Body>
        </Card>
      </div>

      {code && (
        <OrderModal
          open={orderOpen}
          onClose={() => setOrderOpen(false)}
          code={code}
          name={stock.data?.name}
          defaultSide={orderSide}
          suggestedPrice={price || quote.data?.price}
        />
      )}

      <style jsx>{`
        /* 태블릿: 호가창 + 주문 패널만 우측 컬럼으로 합침 */
        @media (max-width: 1280px) {
          div[data-grid='chart-layout'] {
            grid-template-columns: 1fr 320px !important;
          }
          div[data-grid='chart-layout'] [data-area='orderbook'] {
            grid-column: 2;
          }
        }
        /* 모바일: 단일 컬럼, 호가창은 차트 아래로 */
        @media (max-width: 1024px) {
          div[data-grid='chart-layout'] {
            grid-template-columns: 1fr !important;
          }
          div[data-grid='chart-layout'] [data-area='orderbook'] {
            grid-column: auto;
          }
        }
      `}</style>
    </>
  );
}
