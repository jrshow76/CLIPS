import { useMutation, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockCreonStatus, type MockCreonStatus } from '@/lib/mocks/data';
import { toast } from '@/stores/notification-store';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useCreonStatus() {
  return useQuery<MockCreonStatus>({
    queryKey: queryKeys.settings.creon(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockCreonStatus);
      return api.get<MockCreonStatus>('/settings/creon/status');
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useTestCreonConnection() {
  return useMutation({
    mutationFn: async () => {
      if (USE_MOCK) {
        await mockDelay({}, 800);
        return { ok: true, latency_ms: 42 };
      }
      return api.post<{ ok: boolean; latency_ms: number }>('/settings/creon/test');
    },
    onSuccess: (data) => {
      if (data.ok) toast.success('크레온 연결 정상', `응답시간 ${data.latency_ms}ms`);
      else toast.danger('크레온 연결 실패', '관리자에게 문의하세요. (E0071)');
    },
  });
}
