import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { makeMockSectorFlow, mockSectorRotations } from '@/lib/mocks/data';
import type { SectorFlowSeries, SectorRotation } from '@/types/sector-flow';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useSectorFlow() {
  return useQuery<SectorFlowSeries[]>({
    queryKey: queryKeys.market.flow(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(makeMockSectorFlow());
      return api.get<SectorFlowSeries[]>('/sectors/flow');
    },
    staleTime: 60_000,
  });
}

export function useSectorRotation() {
  return useQuery<SectorRotation[]>({
    queryKey: queryKeys.market.rotation(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockSectorRotations);
      return api.get<SectorRotation[]>('/sectors/rotation');
    },
    staleTime: 60_000,
  });
}
