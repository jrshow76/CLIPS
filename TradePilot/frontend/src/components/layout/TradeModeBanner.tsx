'use client';

import { AlertCircle } from 'lucide-react';

import { Banner } from '@/components/ui/banner';
import { useTradeModeStore } from '@/stores/trade-mode-store';

/**
 * LIVE 모드 활성 시 상단에 표시되는 빨간 배너.
 * - 화면 어디서나 LIVE 모드를 인지할 수 있도록 (Designer 원칙: 모드 가시성)
 */
export function TradeModeBanner() {
  const mode = useTradeModeStore((s) => s.mode);
  if (mode !== 'LIVE') return null;
  return (
    <Banner variant="live" icon={<AlertCircle className="h-4 w-4" />}>
      실거래(LIVE) 모드입니다. 모든 주문이 실제 증권사 계좌로 전송됩니다.
    </Banner>
  );
}
