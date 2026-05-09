'use client';

import { useQuery } from '@tanstack/react-query';
import { statsApi } from '@/lib/api/stats';

export function useStatsSummary() {
  return useQuery({
    queryKey: ['stats', 'summary'],
    queryFn: async () => {
      const res = await statsApi.getSummary();
      return res.data.data;
    },
  });
}

export function useMonthlyStats(year?: number) {
  return useQuery({
    queryKey: ['stats', 'monthly', year],
    queryFn: async () => {
      const res = await statsApi.getMonthly(year);
      return res.data.data ?? [];
    },
  });
}

export function useCategoryStats() {
  return useQuery({
    queryKey: ['stats', 'categories'],
    queryFn: async () => {
      const res = await statsApi.getByCategories();
      return res.data.data ?? [];
    },
  });
}
