import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockSignalRules, type MockSignalRule } from '@/lib/mocks/data';
import { toast } from '@/stores/notification-store';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useSignalRules() {
  return useQuery<MockSignalRule[]>({
    queryKey: queryKeys.signalRules.list(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockSignalRules);
      return api.get<MockSignalRule[]>('/signals/rules');
    },
    staleTime: 60_000,
  });
}

export function useSaveSignalRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (rule: Partial<MockSignalRule> & { name: string }) => {
      if (USE_MOCK) {
        const id = rule.id ?? `rule_${Date.now()}`;
        return mockDelay({ ...rule, id } as MockSignalRule);
      }
      if (rule.id) return api.patch<MockSignalRule>(`/signals/rules/${rule.id}`, rule);
      return api.post<MockSignalRule>('/signals/rules', rule);
    },
    onSuccess: () => {
      toast.success('알림 규칙이 저장되었습니다.');
      qc.invalidateQueries({ queryKey: queryKeys.signalRules.all });
    },
  });
}

export function useDeleteSignalRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (USE_MOCK) return mockDelay({ id });
      return api.delete<{ id: string }>(`/signals/rules/${id}`);
    },
    onSuccess: () => {
      toast.success('알림 규칙이 삭제되었습니다.');
      qc.invalidateQueries({ queryKey: queryKeys.signalRules.all });
    },
  });
}
