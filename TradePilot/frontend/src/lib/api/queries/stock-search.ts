import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockStockMaster } from '@/lib/mocks/data';
import { STALE_TIME } from '@/lib/constants';
import type { Stock } from '@/types/stock';

import { USE_MOCK, mockDelay } from './_mock-helpers';

/**
 * 종목 검색 (자동완성용).
 * - 2글자 미만이면 enabled=false로 호출 자제.
 * - 200ms 디바운스는 컴포넌트(StockSearchInput) 책임.
 */
export function useStockSearch(query: string) {
  return useQuery<Stock[]>({
    queryKey: queryKeys.stocks.search(query),
    queryFn: async () => {
      if (USE_MOCK) {
        const q = query.trim().toLowerCase();
        const list = mockStockMaster
          .filter((s) => s.name.toLowerCase().includes(q) || s.code.includes(q))
          .slice(0, 10);
        return mockDelay(list, 120);
      }
      return api.get<Stock[]>('/stocks/search', { params: { q: query, limit: 10 } });
    },
    enabled: query.trim().length >= 1,
    staleTime: STALE_TIME.MASTER,
  });
}
