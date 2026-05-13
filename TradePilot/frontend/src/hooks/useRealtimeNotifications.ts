'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { getNotificationsClient, type NotificationMessage } from '@/lib/realtime/notifications-channel';
import { toast, type ToastVariant } from '@/stores/notification-store';

const SEVERITY_TO_VARIANT: Record<string, ToastVariant> = {
  INFO: 'info',
  SUCCESS: 'success',
  WARN: 'warning',
  CRITICAL: 'danger',
};

/** 시스템/매매 알림 hook (앱 셸에서 1회 호출). */
export function useRealtimeNotifications(): void {
  const qc = useQueryClient();

  useEffect(() => {
    const client = getNotificationsClient();
    client.connect();

    const off = client.on<NotificationMessage>('notification', (msg) => {
      const variant = SEVERITY_TO_VARIANT[msg.severity] ?? 'info';
      toast[variant](msg.title, msg.body ?? undefined);
      // 알림 리스트 다음 조회 시 새 데이터 받게 invalidate
      qc.invalidateQueries({ queryKey: ['notifications'] });
    });
    return off;
  }, [qc]);
}
