import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockNotifications } from '@/lib/mocks/data';
import type { AppNotification } from '@/types/notification';

import { USE_MOCK, mockDelay } from './_mock-helpers';

/**
 * 알림 센터.
 * - 목록 조회, 읽음 처리, 전체 읽음.
 * - 실시간 SSE/WebSocket 연결은 BackendSenior 인계 사항.
 */

export function useNotifications(filter?: { unreadOnly?: boolean }) {
  return useQuery<AppNotification[]>({
    queryKey: queryKeys.notifications.list(filter),
    queryFn: async () => {
      if (USE_MOCK) {
        const list = filter?.unreadOnly ? mockNotifications.filter((n) => !n.read) : mockNotifications;
        return mockDelay(list);
      }
      return api.get<AppNotification[]>('/notifications', { params: filter });
    },
    staleTime: 10_000,
  });
}

export function useUnreadNotificationCount() {
  return useQuery<number>({
    queryKey: queryKeys.notifications.unread(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockNotifications.filter((n) => !n.read).length);
      const r = await api.get<{ count: number }>('/notifications/unread-count');
      return r.count;
    },
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (USE_MOCK) return mockDelay({ id, read: true });
      return api.patch<AppNotification>(`/notifications/${id}`, { read: true });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (USE_MOCK) return mockDelay({ updated: mockNotifications.length });
      return api.post<{ updated: number }>('/notifications/read-all');
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}
