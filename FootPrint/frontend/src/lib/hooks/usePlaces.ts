'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { placesApi } from '@/lib/api/places';
import type { PlaceRequest } from '@/types';

interface PlaceListParams {
  keyword?: string;
  categoryIds?: number[];
  ratingMin?: number;
  page?: number;
  size?: number;
}

export function usePlaceList(params?: PlaceListParams) {
  return useQuery({
    queryKey: ['places', 'list', params],
    queryFn: async () => {
      const res = await placesApi.getList(params);
      return res.data.data;
    },
  });
}

export function usePlaceDetail(id: number) {
  return useQuery({
    queryKey: ['places', 'detail', id],
    queryFn: async () => {
      const res = await placesApi.getById(id);
      return res.data.data;
    },
    enabled: !!id,
  });
}

export function usePlacesInViewport(
  swLat: number,
  swLng: number,
  neLat: number,
  neLng: number,
  enabled = true
) {
  return useQuery({
    queryKey: ['places', 'viewport', { swLat, swLng, neLat, neLng }],
    queryFn: async () => {
      const res = await placesApi.getInViewport(swLat, swLng, neLat, neLng);
      return res.data.data ?? [];
    },
    enabled,
  });
}

export function useCreatePlace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PlaceRequest) => placesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['places'] });
    },
  });
}

export function useUpdatePlace(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PlaceRequest) => placesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['places'] });
    },
  });
}

export function useDeletePlace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => placesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['places'] });
    },
  });
}
