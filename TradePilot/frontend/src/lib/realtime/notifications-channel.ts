/**
 * /ws/notifications 채널.
 */
import { RealtimeClient, type RealtimeMessage } from './ws-client';

import { session } from '@/lib/auth/session';

export interface NotificationMessage extends RealtimeMessage {
  type: 'notification';
  notification_id?: number | null;
  title: string;
  body?: string | null;
  severity: 'INFO' | 'WARN' | 'CRITICAL' | 'SUCCESS';
  event_type?: string | null;
  payload?: Record<string, unknown>;
  ts: string;
}

let _noti: RealtimeClient | null = null;

export function getNotificationsClient(): RealtimeClient {
  if (!_noti) {
    _noti = new RealtimeClient({
      path: '/ws/notifications',
      getToken: () => session.get()?.access_token,
    });
  }
  return _noti;
}

export function disposeNotificationsClient(): void {
  if (_noti) {
    _noti.close();
    _noti = null;
  }
}
