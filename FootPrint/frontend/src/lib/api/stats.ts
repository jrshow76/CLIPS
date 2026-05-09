import { apiClient } from './client';
import type { ApiResponse, StatsSummary, MonthlyStats, CategoryStats } from '@/types';

export const statsApi = {
  getSummary: () =>
    apiClient.get<ApiResponse<StatsSummary>>('/stats/summary'),

  getMonthly: (year?: number) =>
    apiClient.get<ApiResponse<MonthlyStats[]>>('/stats/monthly', {
      params: year ? { year } : undefined,
    }),

  getByCategories: () =>
    apiClient.get<ApiResponse<CategoryStats[]>>('/stats/categories'),
};
