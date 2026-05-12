import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockRecommendations } from '@/lib/mocks/data';
import type { Recommendation } from '@/types/recommendation';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useRecommendations(filter?: { sector?: string; min_score?: number }) {
  return useQuery<Recommendation[]>({
    queryKey: queryKeys.recommendations.list(filter),
    queryFn: async () => {
      if (USE_MOCK) {
        let list = mockRecommendations;
        if (filter?.sector) list = list.filter((r) => r.sector === filter.sector);
        if (filter?.min_score) list = list.filter((r) => r.score >= filter.min_score!);
        return mockDelay(list);
      }
      return api.get<Recommendation[]>('/recommendations', { params: filter });
    },
    staleTime: 60_000,
  });
}
