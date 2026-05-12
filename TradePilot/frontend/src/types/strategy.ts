export type StrategyStatus = 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'ARCHIVED';

export interface StrategyCondition {
  indicator: string; // RSI, MACD, MA20 등
  operator: '<' | '<=' | '=' | '>=' | '>' | 'CROSS_UP' | 'CROSS_DOWN';
  value: number;
  /** AND/OR 결합 (UI에서 자유 조립) */
  combinator?: 'AND' | 'OR';
}

export interface StrategyRule {
  side: 'BUY' | 'SELL';
  conditions: StrategyCondition[];
  qty_mode: 'FIXED' | 'PERCENT' | 'KELLY';
  qty_value: number;
}

export interface Strategy {
  id: string;
  name: string;
  description?: string;
  status: StrategyStatus;
  universe: string[]; // 종목코드 리스트
  rules: StrategyRule[];
  risk_limit?: {
    max_position?: number;
    daily_loss?: number;
  };
  created_at: string;
  updated_at?: string;
}
