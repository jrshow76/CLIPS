/**
 * /ws/market 채널 클라이언트 싱글톤.
 *
 * RealtimeProvider에서 인증 시 init, 로그아웃 시 dispose 호출.
 */
import { RealtimeClient, type RealtimeMessage } from './ws-client';

import { session } from '@/lib/auth/session';

export interface TickMessage extends RealtimeMessage {
  type: 'tick';
  stock_code: string;
  price: number;
  volume: number;
  change: number;
  change_pct: number;
  ts: string;
  event_id?: string | null;
}

let _market: RealtimeClient | null = null;

export function getMarketClient(): RealtimeClient {
  if (!_market) {
    _market = new RealtimeClient({
      path: '/ws/market',
      getToken: () => session.get()?.access_token,
    });
  }
  return _market;
}

export function disposeMarketClient(): void {
  if (_market) {
    _market.close();
    _market = null;
  }
}
