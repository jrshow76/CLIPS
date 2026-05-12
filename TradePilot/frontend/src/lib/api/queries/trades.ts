import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockStrategyPerformance, mockTrades, type MockStrategyPerformance, type MockTrade } from '@/lib/mocks/data';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export interface TradeFilter {
  from?: string;
  to?: string;
  side?: 'BUY' | 'SELL';
  strategy_id?: string;
  code?: string;
}

export function useTrades(filter?: TradeFilter) {
  return useQuery<MockTrade[]>({
    queryKey: queryKeys.trades.list(filter),
    queryFn: async () => {
      if (USE_MOCK) {
        let list = mockTrades;
        if (filter?.side) list = list.filter((t) => t.side === filter.side);
        if (filter?.code) list = list.filter((t) => t.code === filter.code);
        return mockDelay(list);
      }
      return api.get<MockTrade[]>('/trades', { params: filter });
    },
    staleTime: 30_000,
  });
}

export function useStrategyPerformance() {
  return useQuery<MockStrategyPerformance[]>({
    queryKey: queryKeys.strategyPerformance.list(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockStrategyPerformance);
      return api.get<MockStrategyPerformance[]>('/reports/strategies');
    },
    staleTime: 60_000,
  });
}
