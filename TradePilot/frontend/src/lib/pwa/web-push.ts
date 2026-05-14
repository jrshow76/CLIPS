/**
 * Web Push 구독/해제 모듈.
 *
 * 흐름:
 *   1) 백엔드에서 VAPID 공개키 조회 (GET /notifications/push/vapid-public-key)
 *   2) Notification.requestPermission() (사용자 동의)
 *   3) pushManager.subscribe(applicationServerKey)
 *   4) 백엔드에 endpoint/keys 등록 (POST /notifications/push/subscribe)
 *
 * iOS Safari 16.4+ 만 Web Push 가 가능하며, "홈화면에 추가" 한 PWA 컨텍스트에서만 동작한다.
 * 일반 Safari 탭에서는 Notification.permission 자체가 default 로 고정될 수 있다.
 */

import { api } from '@/lib/api/client';
import { getRegistration, isSwSupported } from './service-worker-register';

export type PushSupportLevel = 'full' | 'sw-only' | 'unsupported';

export interface PushCapability {
  level: PushSupportLevel;
  reason?: string;
  isStandalone: boolean;
  iosVersion?: number; // major.minor (e.g. 16.4)
}

export interface PushSubscribeResult {
  ok: boolean;
  endpoint?: string;
  reason?: 'PERMISSION_DENIED' | 'UNSUPPORTED' | 'NO_VAPID_KEY' | 'SUBSCRIBE_FAILED' | 'BACKEND_FAILED' | 'NOT_STANDALONE';
  error?: string;
}

// ============================================================
// 기능 감지
// ============================================================
export function detectPushCapability(): PushCapability {
  if (typeof window === 'undefined') {
    return { level: 'unsupported', reason: 'SSR', isStandalone: false };
  }
  const isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true;

  // iOS 감지
  const ua = window.navigator.userAgent;
  const iosMatch = ua.match(/OS (\d+)_(\d+)/);
  const iosVersion = iosMatch ? Number(`${iosMatch[1]}.${iosMatch[2]}`) : undefined;
  const isIOS = /iPad|iPhone|iPod/.test(ua) || (ua.includes('Mac') && 'ontouchend' in document);

  if (!('serviceWorker' in navigator)) {
    return { level: 'unsupported', reason: 'SW 미지원', isStandalone, iosVersion };
  }
  if (!('PushManager' in window) || !('Notification' in window)) {
    if (isIOS && iosVersion !== undefined && iosVersion < 16.4) {
      return {
        level: 'sw-only',
        reason: 'iOS 16.4 미만은 Web Push 미지원. 이메일/SMS 채널로 폴백됩니다.',
        isStandalone,
        iosVersion,
      };
    }
    return { level: 'unsupported', reason: 'PushManager / Notification API 미지원', isStandalone, iosVersion };
  }
  if (isIOS && !isStandalone) {
    return {
      level: 'sw-only',
      reason: 'iOS 에서는 홈화면 추가 후 PWA 로 실행해야 푸시를 받을 수 있습니다.',
      isStandalone,
      iosVersion,
    };
  }
  return { level: 'full', isStandalone, iosVersion };
}

export function getNotificationPermission(): NotificationPermission | 'unavailable' {
  if (typeof window === 'undefined' || !('Notification' in window)) return 'unavailable';
  return Notification.permission;
}

// ============================================================
// VAPID 공개키
// ============================================================
let _vapidKeyCache: string | null = null;

export async function fetchVapidPublicKey(force = false): Promise<string | null> {
  if (!force && _vapidKeyCache) return _vapidKeyCache;
  try {
    const res = await api.get<{ public_key: string | null }>('/notifications/push/vapid-public-key');
    _vapidKeyCache = res?.public_key || null;
    return _vapidKeyCache;
  } catch (e) {
    console.warn('[pwa] VAPID 공개키 조회 실패', e);
    return null;
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = typeof atob === 'function' ? atob(base64) : Buffer.from(base64, 'base64').toString('binary');
  const output = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    output[i] = rawData.charCodeAt(i);
  }
  return output;
}

// ============================================================
// 구독 / 해제
// ============================================================
export async function getActiveSubscription(): Promise<PushSubscription | null> {
  if (!isSwSupported()) return null;
  const reg = getRegistration() || (await navigator.serviceWorker.ready);
  if (!reg) return null;
  return reg.pushManager.getSubscription();
}

export async function requestPushPermission(): Promise<NotificationPermission> {
  if (typeof window === 'undefined' || !('Notification' in window)) return 'denied';
  if (Notification.permission === 'granted') return 'granted';
  if (Notification.permission === 'denied') return 'denied';
  return Notification.requestPermission();
}

export async function subscribeUserToPush(opts: {
  /** 권한 자동 요청 (false 면 사전 동의된 경우만 진행) */
  requestPermissionIfNeeded?: boolean;
} = {}): Promise<PushSubscribeResult> {
  const cap = detectPushCapability();
  if (cap.level === 'unsupported') {
    return { ok: false, reason: 'UNSUPPORTED', error: cap.reason };
  }
  if (cap.level === 'sw-only') {
    return { ok: false, reason: cap.isStandalone ? 'UNSUPPORTED' : 'NOT_STANDALONE', error: cap.reason };
  }

  const permission = opts.requestPermissionIfNeeded
    ? await requestPushPermission()
    : getNotificationPermission();
  if (permission !== 'granted') {
    return { ok: false, reason: 'PERMISSION_DENIED' };
  }

  const reg = getRegistration() || (await navigator.serviceWorker.ready);
  if (!reg) return { ok: false, reason: 'UNSUPPORTED', error: 'SW 등록되지 않음' };

  const vapidKey = await fetchVapidPublicKey();
  if (!vapidKey) {
    return { ok: false, reason: 'NO_VAPID_KEY', error: 'VAPID 공개키 미설정' };
  }

  let sub: PushSubscription;
  try {
    // applicationServerKey 는 ArrayBuffer/BufferSource 를 받지만 lib.dom 의 일부 버전에서 SharedArrayBuffer 충돌
    const keyBytes = urlBase64ToUint8Array(vapidKey);
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: keyBytes.buffer.slice(
        keyBytes.byteOffset,
        keyBytes.byteOffset + keyBytes.byteLength,
      ) as ArrayBuffer,
    });
  } catch (e) {
    console.warn('[pwa] subscribe 실패', e);
    return { ok: false, reason: 'SUBSCRIBE_FAILED', error: (e as Error).message };
  }

  const body = {
    endpoint: sub.endpoint,
    p256dh_key: extractKey(sub, 'p256dh'),
    auth_key: extractKey(sub, 'auth'),
    user_agent: navigator.userAgent,
    expires_at: sub.expirationTime ? new Date(sub.expirationTime).toISOString() : null,
  };
  try {
    await api.post('/notifications/push/subscribe', body);
    return { ok: true, endpoint: sub.endpoint };
  } catch (e) {
    console.warn('[pwa] 백엔드 구독 등록 실패', e);
    // 백엔드 등록 실패 시 로컬 구독 해제 (orphan 방지)
    try {
      await sub.unsubscribe();
    } catch (_e) {}
    return { ok: false, reason: 'BACKEND_FAILED', error: (e as Error).message };
  }
}

export async function unsubscribeUserFromPush(): Promise<boolean> {
  const sub = await getActiveSubscription();
  if (!sub) return true;
  const endpoint = sub.endpoint;
  try {
    await api.delete('/notifications/push/unsubscribe', { data: { endpoint } });
  } catch (e) {
    console.warn('[pwa] 백엔드 구독 해제 실패 (계속 진행)', e);
  }
  try {
    return sub.unsubscribe();
  } catch (e) {
    return false;
  }
}

/** 테스트 푸시 발송 트리거 */
export async function sendTestPush(): Promise<{ ok: boolean; error?: string }> {
  try {
    await api.post('/notifications/push/test');
    return { ok: true };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

// ============================================================
// 내부 유틸
// ============================================================
function extractKey(sub: PushSubscription, name: 'p256dh' | 'auth'): string {
  const raw = sub.getKey(name);
  if (!raw) return '';
  const bytes = new Uint8Array(raw);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  // URL-safe base64
  const b64 = typeof btoa === 'function' ? btoa(binary) : Buffer.from(binary, 'binary').toString('base64');
  return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}
