import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockSignals } from '@/lib/mocks/data';
import type { Signal } from '@/types/signal';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useSignals(filter?: { action?: 'BUY' | 'SELL'; consumed?: boolean }) {
  return useQuery<Signal[]>({
    queryKey: queryKeys.signals.list(filter),
    queryFn: async () => {
      if (USE_MOCK) {
        let list = mockSignals;
        if (filter?.action) list = list.filter((s) => s.action === filter.action);
        return mockDelay(list);
      }
      return api.get<Signal[]>('/signals', { params: filter });
    },
    staleTime: 10_000,
  });
}
