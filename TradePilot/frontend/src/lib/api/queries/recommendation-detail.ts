import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { makeMockRecommendationDetail, type MockRecommendationDetail } from '@/lib/mocks/data';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useRecommendationDetail(code: string | undefined) {
  return useQuery<MockRecommendationDetail>({
    queryKey: code ? queryKeys.recommendations.detail(code) : ['recommendations', 'detail', 'idle'],
    queryFn: async () => {
      if (!code) throw new Error('code required');
      if (USE_MOCK) return mockDelay(makeMockRecommendationDetail(code));
      return api.get<MockRecommendationDetail>(`/recommendations/${code}`);
    },
    enabled: !!code,
    staleTime: 60_000,
  });
}
