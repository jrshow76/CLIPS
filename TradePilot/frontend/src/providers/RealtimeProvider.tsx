'use client';

import { useEffect, type ReactNode } from 'react';

import { useRealtimeExecution } from '@/hooks/useRealtimeExecution';
import { useRealtimeNotifications } from '@/hooks/useRealtimeNotifications';
import {
  disposeAccountClient,
  disposeMarketClient,
  disposeNotificationsClient,
  getAccountClient,
  getMarketClient,
  getNotificationsClient,
} from '@/lib/realtime';
import { useAuthStore } from '@/stores/auth-store';

/**
 * 실시간 채널 전역 Provider.
 *
 * - 인증 시 3개 채널 자동 connect (멱등)
 * - 로그아웃 시 모든 채널 close
 * - useRealtimeExecution / useRealtimeNotifications를 셸에서 1회만 마운트
 *
 * 종목별 시세는 ``useRealtimeTick(code)``로 컴포넌트가 직접 구독한다.
 */
export function RealtimeProvider({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  // 셸 레벨 1회: execution → toast + cache invalidate, notification → toast
  useRealtimeExecution();
  useRealtimeNotifications();

  useEffect(() => {
    if (!isAuthenticated) {
      // 로그아웃/세션 만료 시 즉시 종료
      disposeMarketClient();
      disposeAccountClient();
      disposeNotificationsClient();
      return;
    }
    // 인증 직후 채널 시작 (멱등)
    getMarketClient().connect();
    getAccountClient().connect();
    getNotificationsClient().connect();

    return () => {
      // Provider 언마운트 시는 dispose 안 함 (페이지 전환 중 끊김 방지).
      // 명시적 로그아웃은 위 분기에서 처리.
    };
  }, [isAuthenticated]);

  return <>{children}</>;
}
