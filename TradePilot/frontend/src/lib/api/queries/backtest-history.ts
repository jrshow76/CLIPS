import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockBacktestHistory, type MockBacktestHistoryItem } from '@/lib/mocks/data';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useBacktestHistory() {
  return useQuery<MockBacktestHistoryItem[]>({
    queryKey: queryKeys.backtestHistory.list(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockBacktestHistory);
      return api.get<MockBacktestHistoryItem[]>('/backtest/history');
    },
    staleTime: 60_000,
  });
}
