export interface Holding {
  code: string;
  name: string;
  sector?: string;
  qty: number;
  avg_price: number;
  current_price: number;
  market_value: number; // qty * current_price
  pnl: number; // (current - avg) * qty
  pnl_pct: number;
  delayed?: boolean;
}

export interface PortfolioSummary {
  total_asset: number; // 평가자산
  cash_balance: number;
  invested: number;
  total_pnl: number;
  total_pnl_pct: number;
  realized_today: number;
  unrealized_today: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  holdings_count: number;
  active_strategies: number;
  active_signals: number;
}

export interface MarketSummary {
  kospi: { value: number; change: number; change_pct: number };
  kosdaq: { value: number; change: number; change_pct: number };
  kospi_volume_value: number; // 거래대금
  kosdaq_volume_value: number;
  foreign_net: number;
  institution_net: number;
  market_status: 'PRE_OPEN' | 'OPEN' | 'LUNCH' | 'CLOSED' | 'AFTER_HOURS';
}
