export type IndicatorType =
  | 'MA'
  | 'EMA'
  | 'BBANDS'
  | 'RSI'
  | 'MACD'
  | 'STOCH'
  | 'ATR'
  | 'OBV';

export interface IndicatorPoint {
  ts: number; // epoch ms
  values: Record<string, number | null>; // ex: { ma5, ma20, upper, lower, middle }
}

export interface IndicatorSeries {
  code: string;
  type: IndicatorType;
  params: Record<string, number>;
  series: IndicatorPoint[];
}
