export type SignalAction = 'BUY' | 'SELL' | 'HOLD';

export type SignalSource =
  | 'GOLDEN_CROSS'
  | 'DEAD_CROSS'
  | 'RSI_OVERSOLD'
  | 'RSI_OVERBOUGHT'
  | 'MACD'
  | 'BOLLINGER_LOWER'
  | 'BOLLINGER_UPPER'
  | 'VOLUME_SPIKE'
  | 'ML_PREDICTION'
  | 'CUSTOM';

export interface Signal {
  id: string;
  code: string;
  name: string;
  action: SignalAction;
  source: SignalSource;
  confidence: number; // 0~100
  price: number;
  strategy_id?: string;
  strategy_name?: string;
  created_at: string; // ISO
  consumed?: boolean;
  note?: string;
}
