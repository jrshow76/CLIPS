/**
 * /ws/orderbook 채널 클라이언트 싱글톤 (호가창 Level 2).
 *
 * - market-channel과 동일 패턴이며 별도 WebSocket 연결을 유지한다.
 * - 차트 페이지처럼 호가창이 필요한 화면에서만 사용 (전역 자동 연결은 RealtimeProvider 결정).
 */
import { RealtimeClient, type RealtimeMessage } from './ws-client';

import { session } from '@/lib/auth/session';

/**
 * 서버 → 클라이언트 호가창 메시지.
 *
 * - ``bids`` / ``asks``: ``[price, qty]`` 10단계 (index 0 = 최우선 호가)
 * - ``total_bid_qty`` / ``total_ask_qty``: 10단계 합산 잔량
 */
export interface OrderbookMessage extends RealtimeMessage {
  type: 'orderbook';
  stock_code: string;
  bids: [number, number][];
  asks: [number, number][];
  total_bid_qty: number;
  total_ask_qty: number;
  ts: string;
  event_id?: string | null;
}

let _orderbook: RealtimeClient | null = null;

export function getOrderbookClient(): RealtimeClient {
  if (!_orderbook) {
    _orderbook = new RealtimeClient({
      path: '/ws/orderbook',
      getToken: () => session.get()?.access_token,
    });
  }
  return _orderbook;
}

export function disposeOrderbookClient(): void {
  if (_orderbook) {
    _orderbook.close();
    _orderbook = null;
  }
}
