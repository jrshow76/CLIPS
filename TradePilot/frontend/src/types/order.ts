import type { TradeMode } from './api';

export type OrderSide = 'BUY' | 'SELL';
export type OrderType = 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT';
export type OrderStatus =
  | 'PENDING'
  | 'ACCEPTED'
  | 'PARTIAL'
  | 'FILLED'
  | 'CANCELED'
  | 'REJECTED'
  | 'EXPIRED';

export interface Order {
  id: string;
  code: string;
  name?: string;
  side: OrderSide;
  order_type: OrderType;
  qty: number;
  filled_qty: number;
  price?: number; // LIMIT 등에서 사용
  avg_fill_price?: number;
  status: OrderStatus;
  mode: TradeMode;
  broker_order_no?: string;
  strategy_id?: string;
  reject_reason?: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateOrderRequest {
  code: string;
  side: OrderSide;
  qty: number;
  order_type: OrderType;
  price?: number;
  stop_price?: number;
  strategy_id?: string;
  /** 클라이언트 발급 (X-Idempotency-Key 헤더로 전송) */
  idempotency_key?: string;
}
