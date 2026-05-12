import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockSectors } from '@/lib/mocks/data';
import type { Sector } from '@/types/recommendation';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useSectors() {
  return useQuery<Sector[]>({
    queryKey: queryKeys.sectors.list(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockSectors);
      return api.get<Sector[]>('/sectors');
    },
    staleTime: 60_000,
  });
}
