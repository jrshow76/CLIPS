import { apiClient } from './client';
import type { ApiResponse, PageResponse, PlaceDetail, PlaceSummary, PlaceRequest } from '@/types';

export const placesApi = {
  getList: (params?: {
    keyword?: string;
    categoryIds?: number[];
    ratingMin?: number;
    page?: number;
    size?: number;
  }) =>
    apiClient.get<ApiResponse<PageResponse<PlaceSummary>>>('/places', { params }),

  getById: (id: number) =>
    apiClient.get<ApiResponse<PlaceDetail>>(`/places/${id}`),

  create: (data: PlaceRequest) =>
    apiClient.post<ApiResponse<PlaceDetail>>('/places', data),

  update: (id: number, data: PlaceRequest) =>
    apiClient.put<ApiResponse<PlaceDetail>>(`/places/${id}`, data),

  delete: (id: number) =>
    apiClient.delete(`/places/${id}`),

  getInViewport: (swLat: number, swLng: number, neLat: number, neLng: number) =>
    apiClient.get<ApiResponse<PlaceSummary[]>>('/places/map', {
      params: { swLat, swLng, neLat, neLng },
    }),
};
