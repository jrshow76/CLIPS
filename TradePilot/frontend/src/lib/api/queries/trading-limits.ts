import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockTradingLimits, type MockTradingLimits } from '@/lib/mocks/data';
import { toast } from '@/stores/notification-store';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useTradingLimits() {
  return useQuery<MockTradingLimits>({
    queryKey: queryKeys.settings.limits(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockTradingLimits);
      return api.get<MockTradingLimits>('/settings/limits');
    },
    staleTime: 30_000,
  });
}

export function useUpdateTradingLimits() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Partial<MockTradingLimits>) => {
      if (USE_MOCK) return mockDelay({ ...mockTradingLimits, ...patch });
      return api.patch<MockTradingLimits>('/settings/limits', patch);
    },
    onSuccess: () => {
      toast.success('매매 한도가 저장되었습니다.');
      qc.invalidateQueries({ queryKey: queryKeys.settings.limits() });
    },
  });
}
