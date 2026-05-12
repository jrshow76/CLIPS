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
import type { Candle, Stock } from '@/types/stock';
import type { AppNotification } from '@/types/notification';
import type { SectorFlowSeries, SectorRotation } from '@/types/sector-flow';

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

/* ============================================================
 *  종목 마스터 (검색 자동완성용)
 * ============================================================ */
export const mockStockMaster: Stock[] = [
  { code: '005930', name: '삼성전자', market: 'KOSPI', sector: '전기·전자', market_cap: 480_000_000_000_000 },
  { code: '000660', name: 'SK하이닉스', market: 'KOSPI', sector: '반도체', market_cap: 120_000_000_000_000 },
  { code: '035720', name: '카카오', market: 'KOSPI', sector: '인터넷' },
  { code: '035420', name: 'NAVER', market: 'KOSPI', sector: '인터넷' },
  { code: '005380', name: '현대차', market: 'KOSPI', sector: '자동차' },
  { code: '068270', name: '셀트리온', market: 'KOSPI', sector: '제약' },
  { code: '051910', name: 'LG화학', market: 'KOSPI', sector: '화학' },
  { code: '005490', name: 'POSCO홀딩스', market: 'KOSPI', sector: '철강' },
  { code: '042700', name: '한미반도체', market: 'KOSPI', sector: '반도체' },
  { code: '247540', name: '에코프로비엠', market: 'KOSDAQ', sector: '2차전지' },
  { code: '373220', name: 'LG에너지솔루션', market: 'KOSPI', sector: '2차전지' },
  { code: '207940', name: '삼성바이오로직스', market: 'KOSPI', sector: '제약' },
  { code: '066570', name: 'LG전자', market: 'KOSPI', sector: '전기·전자' },
  { code: '034730', name: 'SK', market: 'KOSPI', sector: '지주' },
  { code: '105560', name: 'KB금융', market: 'KOSPI', sector: '금융' },
  { code: '055550', name: '신한지주', market: 'KOSPI', sector: '금융' },
  { code: '012330', name: '현대모비스', market: 'KOSPI', sector: '자동차부품' },
  { code: '028260', name: '삼성물산', market: 'KOSPI', sector: '건설' },
  { code: '015760', name: '한국전력', market: 'KOSPI', sector: '전기가스' },
  { code: '032830', name: '삼성생명', market: 'KOSPI', sector: '보험' },
];

/* ============================================================
 *  알림 (Notification Center)
 * ============================================================ */
export const mockNotifications: AppNotification[] = [
  { id: 'noti_01', variant: 'SIGNAL', title: '삼성전자 골든크로스', message: '5일/20일선 골든크로스 매수 시그널이 발생했습니다.', created_at: '2026-05-12T14:21:00+09:00', read: false, link: '/signals' },
  { id: 'noti_02', variant: 'LIMIT', title: '일일 매수 한도 80% 사용', message: '일일 매수 한도(500만원)의 80%를 사용했습니다.', created_at: '2026-05-12T11:08:00+09:00', read: false, link: '/auto-trading/limits' },
  { id: 'noti_03', variant: 'FILL', title: '현대차 매수 체결', message: '현대차 10주 매수 체결 (235,000원).', created_at: '2026-05-12T09:32:00+09:00', read: true, link: '/auto-trading/orders' },
  { id: 'noti_04', variant: 'BACKTEST', title: '백테스트 완료', message: '골든크로스 5/20 전략 백테스트가 완료되었습니다. 수익률 +18.4%', created_at: '2026-05-11T22:14:00+09:00', read: true, link: '/backtest/history' },
  { id: 'noti_05', variant: 'SYSTEM', title: '점검 예고', message: '5/13 02:00~03:00 정기 점검이 예정되어 있습니다.', created_at: '2026-05-11T18:00:00+09:00', read: true },
  { id: 'noti_06', variant: 'NEWS', title: '시장 뉴스', message: '미 연준 금리 동결 결정, 코스피 상승 출발 예상.', created_at: '2026-05-11T08:10:00+09:00', read: true },
];

/* ============================================================
 *  섹터 자금흐름
 * ============================================================ */
export function makeMockSectorFlow(): SectorFlowSeries[] {
  const sectors = [
    { code: 'IT', name: 'IT/전기전자' },
    { code: 'SEMI', name: '반도체' },
    { code: 'BIO', name: '제약/바이오' },
    { code: 'AUTO', name: '자동차' },
    { code: 'BATT', name: '2차전지' },
  ];
  const now = Date.now();
  return sectors.map((s, i) => ({
    code: s.code,
    name: s.name,
    points: Array.from({ length: 20 }).map((_, idx) => ({
      ts: now - (19 - idx) * 86_400_000,
      net: Math.round((Math.sin((idx + i) / 3) + (Math.random() - 0.5)) * 1500),
    })),
  }));
}

export const mockSectorRotations: SectorRotation[] = [
  { from_sector: '반도체', to_sector: '제약/바이오', flow_value: 4_200, intensity: 0.7 },
  { from_sector: '2차전지', to_sector: 'IT/전기전자', flow_value: 2_100, intensity: 0.4 },
  { from_sector: '금융', to_sector: '자동차', flow_value: 1_500, intensity: 0.3 },
  { from_sector: '게임', to_sector: '엔터', flow_value: 800, intensity: 0.2 },
];

/* ============================================================
 *  거래 기록 (Trades)
 * ============================================================ */
export interface MockTrade {
  id: string;
  code: string;
  name: string;
  side: 'BUY' | 'SELL';
  qty: number;
  price: number;
  pnl?: number;
  pnl_pct?: number;
  strategy_name?: string;
  ts: string;
}

export const mockTrades: MockTrade[] = [
  { id: 'trd_001', code: '005930', name: '삼성전자', side: 'BUY', qty: 25, price: 80_200, strategy_name: '골든크로스 5/20', ts: '2026-05-12T09:32:00+09:00' },
  { id: 'trd_002', code: '000660', name: 'SK하이닉스', side: 'SELL', qty: 5, price: 168_500, pnl: -32_500, pnl_pct: -3.71, strategy_name: 'RSI 과매수', ts: '2026-05-12T10:14:00+09:00' },
  { id: 'trd_003', code: '035720', name: '카카오', side: 'BUY', qty: 30, price: 47_800, strategy_name: '볼린저 반등', ts: '2026-05-11T13:08:00+09:00' },
  { id: 'trd_004', code: '005380', name: '현대차', side: 'BUY', qty: 5, price: 235_000, strategy_name: '추세추종', ts: '2026-05-11T11:02:00+09:00' },
  { id: 'trd_005', code: '068270', name: '셀트리온', side: 'SELL', qty: 10, price: 184_300, pnl: 42_000, pnl_pct: 2.34, strategy_name: 'RSI 반등', ts: '2026-05-10T14:55:00+09:00' },
];

/* ============================================================
 *  과거 백테스트 목록
 * ============================================================ */
export interface MockBacktestHistoryItem {
  job_id: string;
  strategy_name: string;
  from: string;
  to: string;
  initial_cash: number;
  total_return_pct: number;
  mdd_pct: number;
  status: 'DONE' | 'FAILED' | 'RUNNING';
  created_at: string;
}

export const mockBacktestHistory: MockBacktestHistoryItem[] = [
  { job_id: 'bt_2025_001', strategy_name: '골든크로스 5/20', from: '2024-01-01', to: '2025-05-01', initial_cash: 10_000_000, total_return_pct: 18.4, mdd_pct: -8.7, status: 'DONE', created_at: '2026-05-10T22:14:00+09:00' },
  { job_id: 'bt_2025_002', strategy_name: 'RSI 과매수/과매도', from: '2024-06-01', to: '2025-05-01', initial_cash: 5_000_000, total_return_pct: -3.2, mdd_pct: -14.1, status: 'DONE', created_at: '2026-05-09T19:00:00+09:00' },
  { job_id: 'bt_2025_003', strategy_name: '볼린저 반등', from: '2025-01-01', to: '2026-05-01', initial_cash: 10_000_000, total_return_pct: 22.7, mdd_pct: -6.2, status: 'DONE', created_at: '2026-05-08T17:30:00+09:00' },
];

/* ============================================================
 *  전략 성과 비교 (report/strategies)
 * ============================================================ */
export interface MockStrategyPerformance {
  strategy_id: string;
  strategy_name: string;
  trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  mdd_pct: number;
  status: 'ACTIVE' | 'PAUSED' | 'ARCHIVED';
}

export const mockStrategyPerformance: MockStrategyPerformance[] = [
  { strategy_id: 'stg_gc_01', strategy_name: '골든크로스 5/20', trades: 48, win_rate: 62.5, total_pnl: 612_000, total_pnl_pct: 6.12, mdd_pct: -4.8, status: 'ACTIVE' },
  { strategy_id: 'stg_rsi_01', strategy_name: 'RSI 과매도 반등', trades: 32, win_rate: 53.1, total_pnl: 218_500, total_pnl_pct: 2.19, mdd_pct: -7.4, status: 'ACTIVE' },
  { strategy_id: 'stg_bb_01', strategy_name: '볼린저 하단 매수', trades: 19, win_rate: 47.4, total_pnl: -98_000, total_pnl_pct: -0.98, mdd_pct: -11.2, status: 'PAUSED' },
];

/* ============================================================
 *  알림 규칙 (signals/rules)
 * ============================================================ */
export interface MockSignalRule {
  id: string;
  name: string;
  indicator: string;
  operator: '<' | '<=' | '=' | '>=' | '>' | 'CROSS_UP' | 'CROSS_DOWN';
  value: number;
  enabled: boolean;
  notify_channel: 'WEB' | 'EMAIL' | 'PUSH';
}

export const mockSignalRules: MockSignalRule[] = [
  { id: 'rule_01', name: 'RSI 과매도', indicator: 'RSI', operator: '<', value: 30, enabled: true, notify_channel: 'WEB' },
  { id: 'rule_02', name: '골든크로스', indicator: 'MA5', operator: 'CROSS_UP', value: 20, enabled: true, notify_channel: 'PUSH' },
  { id: 'rule_03', name: 'MACD 상향 전환', indicator: 'MACD', operator: 'CROSS_UP', value: 0, enabled: false, notify_channel: 'EMAIL' },
];

/* ============================================================
 *  매매 한도
 * ============================================================ */
export interface MockTradingLimits {
  daily_buy_limit: number;
  daily_loss_limit: number;
  max_position_pct: number;
  per_order_limit: number;
  used_buy_today: number;
  used_loss_today: number;
  /** 0~100 진행률 */
  buy_progress: number;
  loss_progress: number;
}

export const mockTradingLimits: MockTradingLimits = {
  daily_buy_limit: 5_000_000,
  daily_loss_limit: -300_000,
  max_position_pct: 30,
  per_order_limit: 1_000_000,
  used_buy_today: 1_842_000,
  used_loss_today: -52_300,
  buy_progress: 36.8,
  loss_progress: 17.4,
};

/* ============================================================
 *  크레온 연결 상태
 * ============================================================ */
export interface MockCreonStatus {
  connected: boolean;
  account_no: string;
  account_alias?: string;
  last_heartbeat: string;
  daily_request_count: number;
  daily_request_limit: number;
  latency_ms: number;
}

export const mockCreonStatus: MockCreonStatus = {
  connected: true,
  account_no: '12345678-01',
  account_alias: '주식거래계좌',
  last_heartbeat: '2026-05-12T14:30:00+09:00',
  daily_request_count: 1_240,
  daily_request_limit: 15_000,
  latency_ms: 38,
};

/* ============================================================
 *  추천주 상세 (시그널/이유/지표)
 * ============================================================ */
export interface MockRecommendationDetail {
  code: string;
  name: string;
  sector?: string;
  price: number;
  change_pct: number;
  score: number;
  reasons: { label: string; detail: string }[];
  indicators: { rsi: number; ma5: number; ma20: number; macd: number; volume_ratio: number };
  target_price: number;
  stop_price: number;
  ai_comment: string;
}

export function makeMockRecommendationDetail(code: string): MockRecommendationDetail {
  const base = mockRecommendations.find((r) => r.code === code) ?? mockRecommendations[0]!;
  return {
    code: base.code,
    name: base.name,
    sector: base.sector,
    price: base.price,
    change_pct: base.change_pct,
    score: base.score,
    reasons: [
      { label: '기술적', detail: base.reason_text },
      { label: '수급', detail: '외국인 5거래일 연속 순매수' },
      { label: '재무', detail: '영업이익 YoY +18.4%' },
    ],
    indicators: {
      rsi: 38.2,
      ma5: Math.round(base.price * 0.99),
      ma20: Math.round(base.price * 0.96),
      macd: 1.42,
      volume_ratio: 1.85,
    },
    target_price: Math.round(base.price * 1.08),
    stop_price: Math.round(base.price * 0.95),
    ai_comment: `${base.name}은(는) 최근 ${base.reason_text}로 단기 반등 가능성이 높은 종목입니다. 단, 시장 변동성에 유의하세요.`,
  };
}

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
