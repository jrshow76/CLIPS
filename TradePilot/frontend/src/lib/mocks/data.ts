/**
 * 정적 Mock 데이터. NEXT_PUBLIC_USE_MOCK=true 시 API queries가 이 데이터를 반환.
 * Designer의 dashboard.html 더미 값과 일치.
 */

import type {
  Holding,
  MarketSummary,
  PortfolioSummary,
} from '@/types/portfolio';
import type { Recommendation } from '@/types/recommendation';
import type { Signal } from '@/types/signal';
import type { Order } from '@/types/order';
import type { Strategy } from '@/types/strategy';
import type { User } from '@/types/user';
import type { Sector } from '@/types/recommendation';
import type { Candle } from '@/types/stock';

export const mockUser: User = {
  id: 'usr_demo_001',
  email: 'demo@tradepilot.kr',
  nickname: '김주식',
  role: 'ROLE_TRADER_PRO',
  trade_mode: 'SIM',
  created_at: '2026-01-15T09:00:00+09:00',
  email_verified: true,
};

export const mockPortfolio: PortfolioSummary = {
  total_asset: 12_348_500,
  cash_balance: 2_148_500,
  invested: 10_200_000,
  total_pnl: 982_300,
  total_pnl_pct: 8.42,
  realized_today: 80_200,
  unrealized_today: 82_100,
  daily_pnl: 162_300,
  daily_pnl_pct: 1.32,
  holdings_count: 5,
  active_strategies: 3,
  active_signals: 5,
};

export const mockHoldings: Holding[] = [
  { code: '005930', name: '삼성전자', sector: '전기·전자', qty: 25, avg_price: 80_200, current_price: 82_500, market_value: 2_062_500, pnl: 57_500, pnl_pct: 2.87 },
  { code: '000660', name: 'SK하이닉스', sector: '반도체', qty: 5, avg_price: 175_000, current_price: 168_500, market_value: 842_500, pnl: -32_500, pnl_pct: -3.71 },
  { code: '035720', name: '카카오', sector: '인터넷', qty: 30, avg_price: 47_800, current_price: 48_300, market_value: 1_449_000, pnl: 15_000, pnl_pct: 1.04, delayed: true },
  { code: '035420', name: 'NAVER', sector: '인터넷', qty: 3, avg_price: 190_500, current_price: 192_000, market_value: 576_000, pnl: 4_500, pnl_pct: 0.78 },
  { code: '005380', name: '현대차', sector: '자동차', qty: 5, avg_price: 235_000, current_price: 238_500, market_value: 1_192_500, pnl: 17_500, pnl_pct: 1.49 },
];

export const mockMarketSummary: MarketSummary = {
  kospi: { value: 2673.15, change: 11.22, change_pct: 0.42 },
  kosdaq: { value: 851.23, change: -2.65, change_pct: -0.31 },
  kospi_volume_value: 8_920_000_000_000,
  kosdaq_volume_value: 5_310_000_000_000,
  foreign_net: 123_800_000_000,
  institution_net: -87_200_000_000,
  market_status: 'OPEN',
};

export const mockRecommendations: Recommendation[] = [
  { code: '068270', name: '셀트리온', sector: '제약', score: 92, price: 184_300, change_pct: 3.2, reason: 'RSI_OVERSOLD', reason_text: 'RSI<30 반등 신호', volume: 1_240_000 },
  { code: '051910', name: 'LG화학', sector: '화학', score: 88, price: 412_000, change_pct: 2.4, reason: 'GOLDEN_CROSS', reason_text: '5/20 골든크로스' },
  { code: '005490', name: 'POSCO홀딩스', sector: '철강', score: 85, price: 412_500, change_pct: 1.9, reason: 'VOLUME_SURGE', reason_text: '거래량 급증 220%' },
  { code: '042700', name: '한미반도체', sector: '반도체', score: 82, price: 138_400, change_pct: 1.2, reason: 'MACD_TURN', reason_text: 'MACD 상향 전환' },
  { code: '247540', name: '에코프로비엠', sector: '2차전지', score: 80, price: 213_000, change_pct: -0.4, reason: 'BOLLINGER_LOWER', reason_text: '볼린저 하단 터치' },
];

export const mockSignals: Signal[] = [
  { id: 'sig_001', code: '005930', name: '삼성전자', action: 'BUY', source: 'GOLDEN_CROSS', confidence: 87, price: 82_500, strategy_name: '골든크로스 전략', created_at: '2026-05-12T14:21:00+09:00' },
  { id: 'sig_002', code: '000660', name: 'SK하이닉스', action: 'SELL', source: 'RSI_OVERBOUGHT', confidence: 71, price: 168_500, strategy_name: 'RSI 과매수', created_at: '2026-05-12T13:55:00+09:00' },
  { id: 'sig_003', code: '373220', name: 'LG에너지솔루션', action: 'BUY', source: 'BOLLINGER_LOWER', confidence: 79, price: 421_000, strategy_name: '볼린저 반등', created_at: '2026-05-12T13:42:00+09:00' },
];

export const mockOrders: Order[] = [
  { id: 'ord_001', code: '005380', name: '현대차', side: 'BUY', order_type: 'MARKET', qty: 10, filled_qty: 10, status: 'FILLED', mode: 'SIM', avg_fill_price: 235_000, created_at: '2026-05-12T09:32:00+09:00' },
  { id: 'ord_002', code: '035720', name: '카카오', side: 'BUY', order_type: 'LIMIT', qty: 30, filled_qty: 30, price: 47_800, status: 'FILLED', mode: 'SIM', avg_fill_price: 47_800, created_at: '2026-05-11T13:08:00+09:00' },
];

export const mockStrategies: Strategy[] = [
  {
    id: 'stg_gc_01',
    name: '골든크로스 5/20',
    description: '5일선과 20일선 교차 시 매수, 데드크로스 시 전량 매도',
    status: 'ACTIVE',
    universe: ['005930', '000660', '035420'],
    rules: [
      { side: 'BUY', conditions: [{ indicator: 'MA5', operator: 'CROSS_UP', value: 20 }], qty_mode: 'PERCENT', qty_value: 10 },
      { side: 'SELL', conditions: [{ indicator: 'MA5', operator: 'CROSS_DOWN', value: 20 }], qty_mode: 'PERCENT', qty_value: 100 },
    ],
    risk_limit: { max_position: 30, daily_loss: -300_000 },
    created_at: '2026-03-01T10:00:00+09:00',
  },
];

export const mockSectors: Sector[] = [
  { code: 'IT', name: 'IT/전기전자', change_pct: 2.1 },
  { code: 'SEMI', name: '반도체', change_pct: -1.8 },
  { code: 'BIO', name: '제약/바이오', change_pct: 3.4 },
  { code: 'CHEM', name: '화학', change_pct: 1.2 },
  { code: 'AUTO', name: '자동차', change_pct: 0.6 },
  { code: 'BANK', name: '금융', change_pct: -0.3 },
  { code: 'STEEL', name: '철강', change_pct: 1.5 },
  { code: 'GAME', name: '게임', change_pct: -2.4 },
  { code: 'ENT', name: '엔터', change_pct: 0.8 },
  { code: 'BATT', name: '2차전지', change_pct: -1.1 },
  { code: 'CON', name: '건설', change_pct: 0.2 },
  { code: 'FOOD', name: '음식료', change_pct: -0.6 },
];

/** 캔들 더미 60개 (1일봉 가정) */
export function makeMockCandles(seed = 80_000, count = 60): Candle[] {
  const out: Candle[] = [];
  let price = seed;
  const now = Date.now();
  for (let i = count - 1; i >= 0; i--) {
    const drift = (Math.sin(i / 4) + (Math.random() - 0.5)) * seed * 0.012;
    const open = price;
    const close = Math.max(open + drift, 1);
    const high = Math.max(open, close) * (1 + Math.random() * 0.008);
    const low = Math.min(open, close) * (1 - Math.random() * 0.008);
    const volume = Math.round((Math.random() * 0.5 + 0.5) * 1_500_000);
    out.push({
      ts: now - i * 86_400_000,
      open: Math.round(open),
      high: Math.round(high),
      low: Math.round(low),
      close: Math.round(close),
      volume,
    });
    price = close;
  }
  return out;
}
