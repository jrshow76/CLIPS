export type MarketCode = 'KOSPI' | 'KOSDAQ' | 'KONEX';

export interface Stock {
  code: string; // "005930" (선행 0 유지)
  name: string;
  market: MarketCode;
  sector?: string;
  market_cap?: number;
}

export interface Quote {
  code: string;
  price: number;
  change: number; // 원 단위
  change_pct: number; // %
  volume: number;
  high?: number;
  low?: number;
  open?: number;
  prev_close?: number;
  ts: number; // epoch ms
  delayed?: boolean;
}

export interface Candle {
  ts: number; // epoch ms
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type CandleInterval = '1m' | '5m' | '15m' | '30m' | 'D' | 'W' | 'M';

export interface OrderbookLevel {
  price: number;
  qty: number;
}

export interface Orderbook {
  code: string;
  ts: number;
  bids: OrderbookLevel[]; // 매수 (높은 가격 순)
  asks: OrderbookLevel[]; // 매도 (낮은 가격 순)
}
