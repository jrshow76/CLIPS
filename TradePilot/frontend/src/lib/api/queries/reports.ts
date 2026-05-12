import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export interface PnlPoint {
  ts: number;
  equity: number;
  pnl: number;
}

export interface PnlSummary {
  total_pnl: number;
  total_pnl_pct: number;
  win_rate: number;
  trades: number;
  best_trade?: number;
  worst_trade?: number;
}

export interface PnlReport {
  summary: PnlSummary;
  series: PnlPoint[];
}

export function usePnlReport(period: '1M' | '3M' | '6M' | '1Y' | 'ALL' = '3M') {
  return useQuery<PnlReport>({
    queryKey: queryKeys.reports.pnl(period),
    queryFn: async () => {
      if (USE_MOCK) {
        const n = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365, ALL: 720 }[period];
        let equity = 10_000_000;
        const series: PnlPoint[] = [];
        const now = Date.now();
        for (let i = n - 1; i >= 0; i--) {
          const change = (Math.random() - 0.45) * 80_000;
          equity += change;
          series.push({ ts: now - i * 86_400_000, equity: Math.round(equity), pnl: Math.round(change) });
        }
        return mockDelay<PnlReport>({
          summary: {
            total_pnl: 982_300,
            total_pnl_pct: 8.42,
            win_rate: 58.3,
            trades: 124,
            best_trade: 142_000,
            worst_trade: -98_500,
          },
          series,
        });
      }
      return api.get<PnlReport>('/reports/pnl', { params: { period } });
    },
  });
}
