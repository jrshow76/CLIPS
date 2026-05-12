export type RecommendationReason =
  | 'RSI_OVERSOLD'
  | 'GOLDEN_CROSS'
  | 'VOLUME_SURGE'
  | 'MACD_TURN'
  | 'BOLLINGER_LOWER'
  | 'ML_TOP_K'
  | 'SECTOR_LEADER';

export interface Recommendation {
  code: string;
  name: string;
  sector?: string;
  score: number; // 0~100
  price: number;
  change_pct: number;
  reason: RecommendationReason;
  reason_text: string;
  volume?: number;
}

export interface Sector {
  code: string;
  name: string;
  change_pct: number;
  market_cap?: number;
  top_stocks?: { code: string; name: string; change_pct: number }[];
}
