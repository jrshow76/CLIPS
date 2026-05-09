'use client';

import { useQuery } from '@tanstack/react-query';
import { categoriesApi } from '@/lib/api/categories';

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const res = await categoriesApi.getList();
      return res.data.data ?? [];
    },
    staleTime: 10 * 60 * 1000,
  });
}
