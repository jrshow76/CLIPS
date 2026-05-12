export type BacktestStatus = 'QUEUED' | 'RUNNING' | 'DONE' | 'FAILED' | 'CANCELED';

export interface BacktestRequest {
  strategy_id: string;
  universe: string[];
  from: string; // YYYY-MM-DD
  to: string;
  initial_cash: number;
  slippage_bps?: number;
  fee_bps?: number;
}

export interface BacktestJob {
  job_id: string;
  status: BacktestStatus;
  progress: number; // 0~100
  started_at?: string;
  finished_at?: string;
  error?: string;
}

export interface BacktestEquityPoint {
  ts: number; // epoch ms
  equity: number;
  benchmark?: number;
}

export interface BacktestResult {
  job_id: string;
  status: BacktestStatus;
  total_return_pct: number;
  cagr_pct: number;
  mdd_pct: number;
  sharpe: number;
  win_rate: number;
  trades: number;
  equity_curve: BacktestEquityPoint[];
}
