'use client';

import { useTradeModeStore } from '@/stores/trade-mode-store';
import { cn } from '@/lib/utils/cn';
import type { TradeMode } from '@/types/api';

/**
 * SIM / LIVE 토글 (헤더용).
 * LIVE 클릭 시 store가 confirmed=false 상태로 setMode를 호출하므로 자동으로 LiveModeModal이 열림.
 */
export function TradeModeToggle() {
  const mode = useTradeModeStore((s) => s.mode);
  const setMode = useTradeModeStore((s) => s.setMode);

  function onClick(target: TradeMode) {
    if (target === mode) return;
    setMode(target); // LIVE 대상이면 자동으로 liveConfirmOpen=true
  }

  return (
    <div className="mode-toggle" role="group" aria-label="매매 모드">
      <button
        type="button"
        className={cn('mode-toggle__item mode-toggle__item--sim', mode === 'SIM' && 'is-active')}
        onClick={() => onClick('SIM')}
      >
        SIM
      </button>
      <button
        type="button"
        className={cn('mode-toggle__item mode-toggle__item--live', mode === 'LIVE' && 'is-active')}
        onClick={() => onClick('LIVE')}
      >
        LIVE
      </button>
    </div>
  );
}
