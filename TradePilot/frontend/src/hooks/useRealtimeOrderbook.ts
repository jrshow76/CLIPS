'use client';

import { useEffect, useMemo, useState } from 'react';

import { getOrderbookClient, type OrderbookMessage } from '@/lib/realtime/orderbook-channel';

/** 호가창 1단계 (price, qty) 행. */
export interface OrderbookLevel {
  price: number;
  qty: number;
}

/** ``useRealtimeOrderbook`` 반환 상태. */
export interface RealtimeOrderbookState {
  /** 매수 10단계 - index 0이 최우선 매수호가 (가장 높은 매수가). */
  bids: OrderbookLevel[];
  /** 매도 10단계 - index 0이 최우선 매도호가 (가장 낮은 매도가). */
  asks: OrderbookLevel[];
  /** 매수 합산 잔량 (10단계 누계). */
  totalBidQty: number;
  /** 매도 합산 잔량 (10단계 누계). */
  totalAskQty: number;
  /** 마지막 수신 timestamp (ISO8601). */
  ts: string | null;
  /** 라이브 데이터 수신 중 여부. */
  isLive: boolean;
}

const INITIAL: RealtimeOrderbookState = {
  bids: [],
  asks: [],
  totalBidQty: 0,
  totalAskQty: 0,
  ts: null,
  isLive: false,
};

/** Mock 호가 생성기 (NEXT_PUBLIC_USE_MOCK=true 시). */
function buildMockOrderbook(code: string): RealtimeOrderbookState {
  // 종목 코드 기반 deterministic 기준가
  let seed = 0;
  for (let i = 0; i < code.length; i += 1) seed = (seed * 31 + code.charCodeAt(i)) >>> 0;
  const base = 50000 + (seed % 50000);
  const tick = base < 5000 ? 5 : base < 20000 ? 10 : base < 50000 ? 50 : 100;
  const bids: OrderbookLevel[] = [];
  const asks: OrderbookLevel[] = [];
  for (let i = 0; i < 10; i += 1) {
    bids.push({ price: base - tick * (i + 1), qty: Math.max(10, 2000 - i * 150) });
    asks.push({ price: base + tick * (i + 1), qty: Math.max(10, 2000 - i * 150) });
  }
  return {
    bids,
    asks,
    totalBidQty: bids.reduce((s, l) => s + l.qty, 0),
    totalAskQty: asks.reduce((s, l) => s + l.qty, 0),
    ts: new Date().toISOString(),
    isLive: true,
  };
}

/**
 * 종목 실시간 호가창 hook.
 *
 * - 마운트 시 ``stockCode`` 자동 구독, 언마운트 시 해제
 * - ``NEXT_PUBLIC_USE_MOCK=true`` 환경에서는 client 연결 없이 mock 데이터 반환
 * - 빈 코드면 no-op
 *
 * 사용:
 * ```tsx
 * const ob = useRealtimeOrderbook('005930');
 * return <OrderBook bids={ob.bids} asks={ob.asks} />;
 * ```
 */
export function useRealtimeOrderbook(
  stockCode: string | undefined | null,
): RealtimeOrderbookState {
  const useMock = useMemo(
    () => process.env.NEXT_PUBLIC_USE_MOCK === 'true',
    [],
  );
  const [state, setState] = useState<RealtimeOrderbookState>(INITIAL);

  useEffect(() => {
    if (!stockCode) {
      setState(INITIAL);
      return;
    }

    if (useMock) {
      // mock 모드: 1초마다 deterministic 호가창 갱신
      setState(buildMockOrderbook(stockCode));
      const id = window.setInterval(() => {
        setState(buildMockOrderbook(stockCode));
      }, 1000);
      return () => window.clearInterval(id);
    }

    const client = getOrderbookClient();
    client.connect(); // 멱등
    client.subscribeStock(stockCode);

    const off = client.on<OrderbookMessage>('orderbook', (msg) => {
      if (msg.stock_code !== stockCode) return;
      setState({
        bids: msg.bids.map(([price, qty]) => ({ price, qty })),
        asks: msg.asks.map(([price, qty]) => ({ price, qty })),
        totalBidQty: msg.total_bid_qty ?? 0,
        totalAskQty: msg.total_ask_qty ?? 0,
        ts: msg.ts,
        isLive: true,
      });
    });

    return () => {
      off();
      // 다른 페이지가 같은 종목을 보고 있을 수 있으므로 unsubscribe는 하지 않는다.
      // (RealtimeProvider가 전역 라이프사이클 관리)
    };
  }, [stockCode, useMock]);

  return state;
}
