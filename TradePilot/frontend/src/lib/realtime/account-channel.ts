/**
 * /ws/account 채널 (체결/주문 상태).
 */
import { RealtimeClient, type RealtimeMessage } from './ws-client';

import { session } from '@/lib/auth/session';

export interface ExecutionMessage extends RealtimeMessage {
  type: 'execution';
  order_id?: string | null;
  broker_order_no?: string | null;
  stock_code: string;
  side: 'BUY' | 'SELL';
  qty: number;
  price: number;
  ts: string;
}

let _account: RealtimeClient | null = null;

export function getAccountClient(): RealtimeClient {
  if (!_account) {
    _account = new RealtimeClient({
      path: '/ws/account',
      getToken: () => session.get()?.access_token,
    });
  }
  return _account;
}

export function disposeAccountClient(): void {
  if (_account) {
    _account.close();
    _account = null;
  }
}
