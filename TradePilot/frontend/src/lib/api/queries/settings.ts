import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { toast } from '@/stores/notification-store';
import { useTradeModeStore } from '@/stores/trade-mode-store';
import type { TradeMode } from '@/types/api';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export interface UserSettings {
  trade_mode: TradeMode;
  notify_on_signal: boolean;
  notify_on_fill: boolean;
  daily_buy_limit: number;
  daily_loss_limit: number;
}

export function useUserSettings() {
  return useQuery<UserSettings>({
    queryKey: queryKeys.settings.me(),
    queryFn: async () => {
      if (USE_MOCK) {
        return mockDelay<UserSettings>({
          trade_mode: 'SIM',
          notify_on_signal: true,
          notify_on_fill: true,
          daily_buy_limit: 5_000_000,
          daily_loss_limit: -300_000,
        });
      }
      return api.get<UserSettings>('/users/me/settings');
    },
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Partial<UserSettings>) => {
      if (USE_MOCK) return mockDelay({ ...patch });
      return api.patch<UserSettings>('/users/me/settings', patch);
    },
    onSuccess: () => {
      toast.success('설정 저장 완료');
      qc.invalidateQueries({ queryKey: queryKeys.settings.me() });
    },
  });
}

/**
 * 매매 모드 전환 mutation.
 * - LIVE 전환은 반드시 LiveModeModal 통과 후 호출 (Trade mode store가 confirmed=true 기록).
 * - 서버 측에서 비밀번호/OTP 재인증을 요구할 수 있다 (E0011).
 */
export function useSwitchTradeMode() {
  const setMode = useTradeModeStore((s) => s.setMode);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (target: TradeMode) => {
      if (USE_MOCK) return mockDelay({ trade_mode: target });
      return api.post<{ trade_mode: TradeMode }>(
        '/settings/trade-mode/switch',
        { target },
        { requireTradeMode: true, headers: { 'X-Trade-Mode': target } },
      );
    },
    onSuccess: (data) => {
      setMode(data.trade_mode, { confirmed: true });
      toast.success(`${data.trade_mode === 'LIVE' ? '실거래' : '시뮬'} 모드로 전환되었습니다.`);
      qc.invalidateQueries({ queryKey: queryKeys.auth.me() });
    },
  });
}
