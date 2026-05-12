import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

import type { TradeMode } from '@/types/api';

/**
 * SIM / LIVE 매매 모드 전역 상태.
 *
 * 정책 (docs/15_trading_policy.md / 22_frontend_structure.md §4.4):
 *  - LIVE 전환은 `LiveModeModal`을 통한 2단계 확인 후 setMode를 호출해야 한다.
 *  - 직접 setMode('LIVE') 호출 시 confirm 플래그를 강제하여 우회 방지.
 *  - axios 인터셉터(client.ts)가 이 상태를 읽어 X-Trade-Mode 헤더로 자동 주입.
 *  - 서버 응답 E0006(모드 불일치) 발생 시 모드 재동기화 후 사용자에게 재확인 요청.
 */

interface TradeModeState {
  mode: TradeMode;
  /** LIVE 전환 모달 노출 여부 (UI 트리거) */
  liveConfirmOpen: boolean;
  setMode: (mode: TradeMode, opts?: { confirmed?: boolean }) => void;
  openLiveConfirm: () => void;
  closeLiveConfirm: () => void;
}

export const useTradeModeStore = create<TradeModeState>()(
  persist(
    (set) => ({
      mode: 'SIM',
      liveConfirmOpen: false,
      setMode: (mode, opts) => {
        // LIVE 전환은 확인 플래그 필수.
        if (mode === 'LIVE' && !opts?.confirmed) {
          set({ liveConfirmOpen: true });
          return;
        }
        set({ mode, liveConfirmOpen: false });
      },
      openLiveConfirm: () => set({ liveConfirmOpen: true }),
      closeLiveConfirm: () => set({ liveConfirmOpen: false }),
    }),
    {
      name: 'tp.trade-mode',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ mode: state.mode }),
    },
  ),
);
