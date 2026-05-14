/**
 * PWA 모듈 진입점.
 */
export {
  registerServiceWorker,
  activatePendingServiceWorker,
  clearAllCaches,
  unregisterServiceWorker,
  isSwSupported,
  getRegistration,
  type SwLifecycle,
} from './service-worker-register';

export {
  detectPushCapability,
  getNotificationPermission,
  fetchVapidPublicKey,
  getActiveSubscription,
  requestPushPermission,
  subscribeUserToPush,
  unsubscribeUserFromPush,
  sendTestPush,
  type PushSupportLevel,
  type PushCapability,
  type PushSubscribeResult,
} from './web-push';

export {
  initInstallPromptCapture,
  onInstallPromptChange,
  triggerInstallPrompt,
  dismissInstallPrompt,
  hasDeferredPrompt,
  shouldShowBanner,
  isStandalone,
  isIOS,
  getInstallStatus,
  type InstallStatus,
} from './install-prompt';
