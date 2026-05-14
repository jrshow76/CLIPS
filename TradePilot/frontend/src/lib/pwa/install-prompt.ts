/**
 * PWA 설치 프롬프트 관리.
 *
 * - Chrome/Edge/Android: `beforeinstallprompt` 이벤트 캐치 → prompt() 트리거
 * - iOS Safari: beforeinstallprompt 미지원. "공유 → 홈화면에 추가" 안내 UI 노출만 가능.
 * - 사용자 거절 또는 설치 완료 후 일정 기간 재노출 금지 (localStorage 플래그)
 */

const DISMISS_KEY = 'tp.pwa.install_dismissed_at';
const INSTALLED_KEY = 'tp.pwa.installed_at';
const REPROMPT_DAYS = 14;

// BeforeInstallPromptEvent 는 표준 lib.dom.d.ts 에 아직 없음
type BeforeInstallPromptEvent = Event & {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
  prompt: () => Promise<void>;
};

let _deferredPrompt: BeforeInstallPromptEvent | null = null;
const _listeners = new Set<() => void>();

export function isInstallPromptSupported(): boolean {
  return typeof window !== 'undefined' && 'BeforeInstallPromptEvent' in window === false
    ? false // 일부 브라우저는 이벤트만 발생시키므로 별도 감지 필요 — 아래 hasDeferred 로 판단
    : true;
}

export function hasDeferredPrompt(): boolean {
  return !!_deferredPrompt;
}

export function isStandalone(): boolean {
  if (typeof window === 'undefined') return false;
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

export function isIOS(): boolean {
  if (typeof window === 'undefined') return false;
  const ua = window.navigator.userAgent;
  return /iPad|iPhone|iPod/.test(ua) || (ua.includes('Mac') && 'ontouchend' in document);
}

export function shouldShowBanner(): boolean {
  if (typeof window === 'undefined') return false;
  if (isStandalone()) return false;
  if (localStorage.getItem(INSTALLED_KEY)) return false;
  const dismissedAt = Number(localStorage.getItem(DISMISS_KEY) || 0);
  if (dismissedAt) {
    const diffDays = (Date.now() - dismissedAt) / (1000 * 60 * 60 * 24);
    if (diffDays < REPROMPT_DAYS) return false;
  }
  // 안드로이드/Chrome 은 deferred prompt 보유 시, iOS 는 보유 여부와 무관하게 안내
  return hasDeferredPrompt() || isIOS();
}

export function initInstallPromptCapture(): () => void {
  if (typeof window === 'undefined') return () => {};
  const handler = (e: Event) => {
    e.preventDefault();
    _deferredPrompt = e as BeforeInstallPromptEvent;
    _listeners.forEach((fn) => fn());
  };
  window.addEventListener('beforeinstallprompt', handler);

  const installedHandler = () => {
    localStorage.setItem(INSTALLED_KEY, String(Date.now()));
    _deferredPrompt = null;
    _listeners.forEach((fn) => fn());
  };
  window.addEventListener('appinstalled', installedHandler);

  return () => {
    window.removeEventListener('beforeinstallprompt', handler);
    window.removeEventListener('appinstalled', installedHandler);
  };
}

export function onInstallPromptChange(fn: () => void): () => void {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

export async function triggerInstallPrompt(): Promise<'accepted' | 'dismissed' | 'unavailable'> {
  if (!_deferredPrompt) return 'unavailable';
  await _deferredPrompt.prompt();
  const choice = await _deferredPrompt.userChoice;
  if (choice.outcome === 'accepted') {
    localStorage.setItem(INSTALLED_KEY, String(Date.now()));
  } else {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
  }
  _deferredPrompt = null;
  _listeners.forEach((fn) => fn());
  return choice.outcome;
}

export function dismissInstallPrompt(): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(DISMISS_KEY, String(Date.now()));
  _deferredPrompt = null;
  _listeners.forEach((fn) => fn());
}

export interface InstallStatus {
  standalone: boolean;
  installed: boolean;
  promptAvailable: boolean;
  ios: boolean;
  dismissedAt: number | null;
  installedAt: number | null;
}

export function getInstallStatus(): InstallStatus {
  if (typeof window === 'undefined') {
    return {
      standalone: false,
      installed: false,
      promptAvailable: false,
      ios: false,
      dismissedAt: null,
      installedAt: null,
    };
  }
  return {
    standalone: isStandalone(),
    installed: !!localStorage.getItem(INSTALLED_KEY) || isStandalone(),
    promptAvailable: hasDeferredPrompt(),
    ios: isIOS(),
    dismissedAt: Number(localStorage.getItem(DISMISS_KEY) || 0) || null,
    installedAt: Number(localStorage.getItem(INSTALLED_KEY) || 0) || null,
  };
}
