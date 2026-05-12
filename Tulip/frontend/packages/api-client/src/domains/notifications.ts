/**
 * notifications 도메인 모듈
 *
 * Phase 1-D 단계에서는 실시간 채널 백엔드가 없으므로 polling 으로 대체한다.
 * SSE 전환은 백엔드 notification-service 완료 시(Phase 2) `subscribe()` 구현만 교체.
 *
 * 추상화:
 *   - useNotificationsQuery: 미확인·읽지 않은 알림 목록 (polling)
 *   - useNotificationsStream: SSE 인터페이스(현재는 polling으로 폴백)
 */
import { useEffect, useRef, useState } from 'react';
import { useQuery, type UseQueryOptions } from '@tanstack/react-query';

import { useApiClient } from '../context';
import type { ApiError } from '../errors';
import { isMockMode, mockDelay } from '../mock';

// ───────────────────────────── 타입 ─────────────────────────────

export type NotificationSeverity = 'info' | 'success' | 'warning' | 'danger';

export interface NotificationItem {
  id: string;
  severity: NotificationSeverity;
  title: string;
  body?: string;
  /** 도메인 컨텍스트 (ACS/CIR/FAC 등) */
  domain?: string;
  href?: string;
  read: boolean;
  occurredAt: string;
}

export interface NotificationsQuery {
  /** 미확인만 가져오기 */
  unreadOnly?: boolean;
  limit?: number;
}

// ───────────────────────────── Mock ─────────────────────────────

const MOCK_NOTIFICATIONS: NotificationItem[] = [
  {
    id: 'nfc_1',
    severity: 'danger',
    title: '연체 7건 발생',
    body: '오늘 반납 예정 중 미반납이 7건 있습니다.',
    domain: 'CIR',
    href: '/circulation/overdue',
    read: false,
    occurredAt: new Date(Date.now() - 5 * 60_000).toISOString(),
  },
  {
    id: 'nfc_2',
    severity: 'info',
    title: '신규 회원 12명 가입',
    body: '오늘 신규 가입한 회원이 12명입니다.',
    domain: 'ACS',
    href: '/access/members',
    read: false,
    occurredAt: new Date(Date.now() - 35 * 60_000).toISOString(),
  },
  {
    id: 'nfc_3',
    severity: 'warning',
    title: '코드 정책 변경 승인 대기',
    body: 'BOOK_STATUS 변경이 승인 대기 중입니다.',
    domain: 'SYS',
    href: '/codes',
    read: false,
    occurredAt: new Date(Date.now() - 2 * 3600_000).toISOString(),
  },
  {
    id: 'nfc_4',
    severity: 'success',
    title: '월간 통계 배치 완료',
    domain: 'SYS',
    read: true,
    occurredAt: new Date(Date.now() - 8 * 3600_000).toISOString(),
  },
];

// ───────────────────────────── Query Keys ─────────────────────────────

export const notificationKeys = {
  all: ['notifications'] as const,
  list: (q: NotificationsQuery) => [...notificationKeys.all, 'list', q] as const,
};

// ───────────────────────────── Hooks ─────────────────────────────

export function useNotificationsQuery(
  params: NotificationsQuery = {},
  options?: Omit<UseQueryOptions<NotificationItem[], ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<NotificationItem[], ApiError>({
    queryKey: notificationKeys.list(params),
    queryFn: () => {
      if (isMockMode()) {
        let items = [...MOCK_NOTIFICATIONS];
        if (params.unreadOnly) items = items.filter((n) => !n.read);
        if (params.limit) items = items.slice(0, params.limit);
        return mockDelay(items, 200);
      }
      const query: Record<string, unknown> = {};
      if (params.unreadOnly) query.unreadOnly = true;
      if (params.limit) query.limit = params.limit;
      return client.get<NotificationItem[]>('/notifications', { query });
    },
    // polling 기반 실시간 갱신 (Phase 2에서 SSE로 교체)
    refetchInterval: 5_000,
    refetchIntervalInBackground: false,
    staleTime: 4_000,
    ...options,
  });
}

/**
 * SSE 구독 인터페이스 (현재는 polling 폴백).
 *
 * `onEvent`로 새 알림 도착 시 콜백을 받는다.
 * Phase 2에서 EventSource('/api/v1/notifications/stream') 로 전환.
 */
export interface NotificationsStreamOptions {
  onEvent?: (item: NotificationItem) => void;
  /** polling 간격 (ms) — 기본 5초 */
  intervalMs?: number;
  enabled?: boolean;
}

export function useNotificationsStream(opts: NotificationsStreamOptions = {}): {
  connected: boolean;
} {
  const { onEvent, intervalMs = 5_000, enabled = true } = opts;
  const [connected, setConnected] = useState(false);
  const seenRef = useRef<Set<string>>(new Set());
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    setConnected(true);

    async function tick() {
      try {
        if (isMockMode()) {
          // mock: 랜덤하게 신규 항목 도착 시뮬레이션
          const item = MOCK_NOTIFICATIONS.find((n) => !seenRef.current.has(n.id));
          if (item) {
            seenRef.current.add(item.id);
            onEventRef.current?.(item);
          }
        }
        // 실 API에서는 fetch 결과를 diff하여 신규만 emit
      } catch {
        /* swallow polling errors */
      }
    }
    void tick();
    const handle = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      setConnected(false);
      clearInterval(handle);
      void cancelled;
    };
  }, [enabled, intervalMs]);

  return { connected };
}
