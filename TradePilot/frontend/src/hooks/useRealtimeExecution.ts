'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { getAccountClient, type ExecutionMessage } from '@/lib/realtime/account-channel';
import { toast } from '@/stores/notification-store';

/**
 * 체결 알림 hook.
 *
 * - 체결 메시지 수신 시 toast + TanStack Query 캐시 무효화
 * - 보통 앱 셸(Layout 레벨)에서 1번만 호출
 */
export function useRealtimeExecution(): void {
  const qc = useQueryClient();

  useEffect(() => {
    const client = getAccountClient();
    client.connect();

    const off = client.on<ExecutionMessage>('execution', (msg) => {
      const sideKr = msg.side === 'BUY' ? '매수' : '매도';
      toast.success(
        `${sideKr} 체결`,
        `${msg.stock_code} ${msg.qty.toLocaleString('ko-KR')}주 @ ${msg.price.toLocaleString('ko-KR')}원`,
      );
      // 보유/주문/포트폴리오/리포트 캐시 무효화
      qc.invalidateQueries({ queryKey: ['portfolio', 'summary'] });
      qc.invalidateQueries({ queryKey: ['portfolio', 'holdings'] });
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['orders', 'executions'] });
      qc.invalidateQueries({ queryKey: ['reports'] });
    });
    return off;
  }, [qc]);
}
