import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockStrategies } from '@/lib/mocks/data';
import { toast } from '@/stores/notification-store';
import type { Strategy } from '@/types/strategy';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useStrategies() {
  return useQuery<Strategy[]>({
    queryKey: queryKeys.strategies.list(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockStrategies);
      return api.get<Strategy[]>('/strategies');
    },
  });
}

export function useStrategy(id: string | undefined) {
  return useQuery<Strategy>({
    queryKey: id ? queryKeys.strategies.detail(id) : ['strategies', 'detail', 'idle'],
    queryFn: async () => {
      if (!id) throw new Error('id required');
      if (USE_MOCK) {
        const found = mockStrategies.find((s) => s.id === id) ?? mockStrategies[0];
        return mockDelay<Strategy>(found);
      }
      return api.get<Strategy>(`/strategies/${id}`);
    },
    enabled: !!id,
  });
}

export function useSaveStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (strategy: Partial<Strategy>) => {
      if (USE_MOCK) return mockDelay<Strategy>({ ...(mockStrategies[0] as Strategy), ...strategy });
      if (strategy.id) return api.patch<Strategy>(`/strategies/${strategy.id}`, strategy);
      return api.post<Strategy>('/strategies', strategy);
    },
    onSuccess: () => {
      toast.success('전략 저장 완료');
      qc.invalidateQueries({ queryKey: queryKeys.strategies.all });
    },
  });
}
