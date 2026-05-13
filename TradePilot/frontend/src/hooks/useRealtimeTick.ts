'use client';

import { useEffect, useState } from 'react';

import { getMarketClient, type TickMessage } from '@/lib/realtime/market-channel';

export interface RealtimeTickState {
  /** 현재 가격 (서버에서 수신한 마지막 값) */
  price: number | null;
  /** 누적 거래량 */
  volume: number;
  /** 등락 (원) */
  change: number;
  /** 등락률 (%) */
  changePct: number;
  /** 마지막 수신 timestamp (ISO8601) */
  ts: string | null;
  /** 라이브 데이터 수신 중 여부 */
  isLive: boolean;
}

const INITIAL: RealtimeTickState = {
  price: null,
  volume: 0,
  change: 0,
  changePct: 0,
  ts: null,
  isLive: false,
};

/**
 * 종목 실시간 시세 hook.
 *
 * - 마운트 시 ``stockCode`` 자동 구독, 언마운트 시 해제
 * - 빈 코드면 no-op
 * - 다중 종목 동시 구독은 hook을 종목별로 호출
 *
 * 사용:
 * ```tsx
 * const tick = useRealtimeTick('005930');
 * return <span>{tick.price?.toLocaleString()}</span>;
 * ```
 */
export function useRealtimeTick(stockCode: string | undefined | null): RealtimeTickState {
  const [state, setState] = useState<RealtimeTickState>(INITIAL);

  useEffect(() => {
    if (!stockCode) {
      setState(INITIAL);
      return;
    }
    const client = getMarketClient();
    client.connect(); // 멱등
    client.subscribeStock(stockCode);

    const off = client.on<TickMessage>('tick', (msg) => {
      if (msg.stock_code !== stockCode) return;
      setState({
        price: msg.price,
        volume: msg.volume ?? 0,
        change: msg.change ?? 0,
        changePct: msg.change_pct ?? 0,
        ts: msg.ts,
        isLive: true,
      });
    });

    return () => {
      off();
      // 다른 곳에서 같은 종목을 보고 있을 수 있으므로
      // 단순 hook unmount에서는 unsubscribe 안 함.
      // (RealtimeProvider가 채널을 전역 관리)
    };
  }, [stockCode]);

  return state;
}
