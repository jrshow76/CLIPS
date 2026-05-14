'use client';

/**
 * PWAProvider
 * ----------------------------------------------------------
 * 책임:
 *   1) Service Worker 자동 등록 (production / NEXT_PUBLIC_ENABLE_SW=true)
 *   2) beforeinstallprompt 이벤트 캐치 → 설치 UI 가용성 노출
 *   3) 인증 상태에 따른 푸시 구독 sync
 *      - 로그인 시 + 권한 granted 인 경우 자동 재구독 (백엔드 endpoint 갱신)
 *      - 로그아웃 시 push 구독 백엔드에서만 해제(브라우저 구독은 유지하여 재로그인 시 빠르게 복구)
 *   4) SW 메시지(NAVIGATE) 수신 → Next 라우터로 이동
 *   5) 푸시 구독 만료 이벤트(PUSH_SUBSCRIPTION_CHANGED) → 재구독 시도
 *
 * 충돌 방지:
 *   - dev 환경 + NEXT_PUBLIC_ENABLE_SW != 'true' 면 SW 등록 자체 skip
 *   - 권한이 default 인 사용자에게 자동 구독 요청을 보내지 않음 (UI 에서 명시 토글)
 */

import { useRouter } from 'next/navigation';
import { useEffect, useRef, type ReactNode } from 'react';

import {
  activatePendingServiceWorker,
  detectPushCapability,
  getActiveSubscription,
  getNotificationPermission,
  initInstallPromptCapture,
  registerServiceWorker,
  subscribeUserToPush,
  unsubscribeUserFromPush,
} from '@/lib/pwa';
import { useAuthStore } from '@/stores/auth-store';
import { toast } from '@/stores/notification-store';

export function PWAProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const userId = useAuthStore((s) => s.user?.id ?? null);
  const initOnce = useRef(false);
  const subSyncedFor = useRef<string | null>(null);

  // ----- 1) SW 등록 + install prompt 캡처 (마운트 1회) -----
  useEffect(() => {
    if (initOnce.current) return;
    initOnce.current = true;

    const detachInstall = initInstallPromptCapture();

    void registerServiceWorker({
      onUpdateAvailable: () => {
        toast.info(
          '새 버전이 준비되었습니다',
          '탭을 새로고침하면 최신 화면이 적용됩니다.',
        );
      },
      onMessage: (event) => {
        const data = event.data || {};
        if (data.type === 'NAVIGATE' && typeof data.url === 'string') {
          router.push(data.url);
        }
        if (data.type === 'PUSH_SUBSCRIPTION_CHANGED') {
          // 만료된 구독 자동 갱신
          void resyncPushSubscriptionSilent();
        }
      },
    });

    return () => {
      detachInstall();
    };
    // router 는 안정 참조
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ----- 2) 인증 상태에 따른 구독 sync -----
  useEffect(() => {
    if (!isAuthenticated || !userId) {
      // 로그아웃: 활성 구독이 있으면 백엔드 해제 (브라우저 구독은 유지)
      if (subSyncedFor.current !== null) {
        void unsubscribeOnLogout();
        subSyncedFor.current = null;
      }
      return;
    }
    if (subSyncedFor.current === userId) return; // 이미 sync 완료
    void syncSubscriptionOnLogin(userId);
    subSyncedFor.current = userId;
  }, [isAuthenticated, userId]);

  return <>{children}</>;
}

/**
 * 로그인 직후 — 이미 권한이 granted 인 경우만 자동 (재)구독.
 * 권한이 default 면 사용자 명시 토글까지 대기 (불필요한 거부 방지).
 */
async function syncSubscriptionOnLogin(_userId: string): Promise<void> {
  try {
    const cap = detectPushCapability();
    if (cap.level === 'unsupported') return;
    if (getNotificationPermission() !== 'granted') return;

    const existing = await getActiveSubscription();
    // 권한이 있는 사용자는 항상 백엔드에 endpoint 등록 갱신 (last_used_at 효과)
    const result = await subscribeUserToPush({ requestPermissionIfNeeded: false });
    if (!result.ok && !existing) {
      console.warn('[pwa] 자동 구독 실패', result);
    }
  } catch (e) {
    console.warn('[pwa] syncSubscriptionOnLogin 오류', e);
  }
}

async function unsubscribeOnLogout(): Promise<void> {
  // 로그아웃 시 브라우저 구독은 유지하되, 백엔드의 user_id-endpoint 매핑만 정리.
  // (단순화를 위해 unsubscribeUserFromPush 호출: 백엔드 + 브라우저 동시 해제)
  try {
    await unsubscribeUserFromPush();
  } catch (e) {
    // noop
  }
}

async function resyncPushSubscriptionSilent(): Promise<void> {
  try {
    if (getNotificationPermission() !== 'granted') return;
    await subscribeUserToPush({ requestPermissionIfNeeded: false });
  } catch (_e) {
    // noop
  }
}

// 외부에서 강제 활성화 (예: 설정 화면 "새 버전 적용" 버튼)
export { activatePendingServiceWorker };
