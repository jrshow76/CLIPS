import { apiClient } from './client';
import type { ApiResponse, Category } from '@/types';

export interface CategoryRequest {
  name: string;
  color: string;
  icon: string;
  sortOrder?: number;
}

export const categoriesApi = {
  getList: () =>
    apiClient.get<ApiResponse<Category[]>>('/categories'),

  getById: (id: number) =>
    apiClient.get<ApiResponse<Category>>(`/categories/${id}`),

  create: (data: CategoryRequest) =>
    apiClient.post<ApiResponse<Category>>('/categories', data),

  update: (id: number, data: Partial<CategoryRequest>) =>
    apiClient.put<ApiResponse<Category>>(`/categories/${id}`, data),

  delete: (id: number) =>
    apiClient.delete(`/categories/${id}`),
};
