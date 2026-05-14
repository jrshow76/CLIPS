/**
 * Service Worker 등록 및 업데이트 감지.
 *
 * - 프로덕션 빌드(NODE_ENV !== 'development') 또는 ENABLE_SW=true 일 때만 등록.
 * - dev 환경에서는 HMR 충돌 회피를 위해 기본 비활성. 활성화 옵션 제공.
 * - 새 SW 버전 감지 시 콜백을 통해 사용자에게 새로고침을 권유한다.
 *
 * 참고:
 *   - SW 는 `/sw.js` 정적 자산으로만 노출 (Next.js `public/`)
 *   - scope = '/' 로 전체 앱을 컨트롤
 *   - iOS Safari 는 SW 등록 자체는 11.3+ 지원이지만, Push 는 16.4+ 만 동작
 */

export type SwLifecycle = 'idle' | 'registering' | 'active' | 'updating' | 'updated' | 'error';

export interface RegisterSwOptions {
  /** 새 SW 버전이 사용 가능할 때 호출됨 (사용자에게 알림 UI 표시 권장) */
  onUpdateAvailable?: (registration: ServiceWorkerRegistration) => void;
  /** SW 로부터 메시지를 받았을 때 호출 (예: NAVIGATE 라우팅) */
  onMessage?: (event: MessageEvent) => void;
  /** 상태 변화 콜백 */
  onLifecycleChange?: (state: SwLifecycle) => void;
  /** 등록 경로 (기본 /sw.js) */
  swUrl?: string;
}

let _registration: ServiceWorkerRegistration | null = null;

export function isSwSupported(): boolean {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator;
}

export function getRegistration(): ServiceWorkerRegistration | null {
  return _registration;
}

/**
 * SW 를 등록한다. 이미 등록되어 있으면 기존 등록을 반환.
 * dev 모드에서는 ENABLE_SW=true 가 아닌 경우 no-op.
 */
export async function registerServiceWorker(
  opts: RegisterSwOptions = {},
): Promise<ServiceWorkerRegistration | null> {
  const { onUpdateAvailable, onMessage, onLifecycleChange, swUrl = '/sw.js' } = opts;
  if (!isSwSupported()) {
    onLifecycleChange?.('error');
    return null;
  }
  // dev 모드 가드: Next.js 빌드 산출물이 자주 바뀌어 SW 캐시 충돌 방지
  const isDev = process.env.NODE_ENV === 'development';
  const allowDevSw = process.env.NEXT_PUBLIC_ENABLE_SW === 'true';
  if (isDev && !allowDevSw) {
    onLifecycleChange?.('idle');
    return null;
  }

  try {
    onLifecycleChange?.('registering');
    const reg = await navigator.serviceWorker.register(swUrl, { scope: '/' });
    _registration = reg;
    onLifecycleChange?.('active');

    // 업데이트 감지
    reg.addEventListener('updatefound', () => {
      const installing = reg.installing;
      if (!installing) return;
      onLifecycleChange?.('updating');
      installing.addEventListener('statechange', () => {
        if (installing.state === 'installed' && navigator.serviceWorker.controller) {
          onLifecycleChange?.('updated');
          onUpdateAvailable?.(reg);
        }
      });
    });

    // SW 에서 보낸 메시지 처리
    if (onMessage) {
      navigator.serviceWorker.addEventListener('message', onMessage);
    }

    // controllerchange: skipWaiting 적용 후 새 SW 가 컨트롤 잡으면 리로드 권유
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      // 일부 케이스에서 페이지 리로드가 안전 (Workbox 패턴)
      // 자동 reload 는 주의: 사용자의 작업 상태 잃을 수 있으므로 명시적 콜백으로만 처리
    });

    return reg;
  } catch (err) {
    console.warn('[pwa] SW 등록 실패', err);
    onLifecycleChange?.('error');
    return null;
  }
}

/**
 * 새 SW 버전 활성화: 대기 중인 SW 에 SKIP_WAITING 을 보내고 reload.
 */
export async function activatePendingServiceWorker(): Promise<void> {
  if (!_registration?.waiting) return;
  _registration.waiting.postMessage({ type: 'SKIP_WAITING' });
  // 잠시 후 리로드 (controllerchange 후가 더 안전하지만 UX 단순화)
  setTimeout(() => window.location.reload(), 300);
}

/**
 * 모든 캐시 정리 요청.
 */
export async function clearAllCaches(): Promise<boolean> {
  if (!isSwSupported() || !navigator.serviceWorker.controller) {
    // SW 없을 때는 직접 Cache API 호출
    if (typeof caches === 'undefined') return false;
    const keys = await caches.keys();
    await Promise.all(keys.map((k) => caches.delete(k)));
    return true;
  }
  return new Promise<boolean>((resolve) => {
    const channel = new MessageChannel();
    channel.port1.onmessage = (e) => resolve(!!e.data?.ok);
    navigator.serviceWorker.controller!.postMessage(
      { type: 'CLEAR_CACHES' },
      [channel.port2],
    );
    setTimeout(() => resolve(false), 5000); // 안전망
  });
}

/**
 * SW 등록 해제 (디버그/테스트용).
 */
export async function unregisterServiceWorker(): Promise<boolean> {
  if (!isSwSupported()) return false;
  const regs = await navigator.serviceWorker.getRegistrations();
  const results = await Promise.all(regs.map((r) => r.unregister()));
  _registration = null;
  return results.every(Boolean);
}
