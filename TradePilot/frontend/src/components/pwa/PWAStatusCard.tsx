'use client';

/**
 * 설정 화면 — PWA 상태 카드.
 * - 설치 상태(standalone / 설치 가능 / 설치 완료)
 * - 푸시 알림 권한 + 토글
 * - 캐시 정리 버튼
 * - 테스트 푸시 발송
 * - 새 SW 버전 적용 버튼
 */

import { BellRing, Download, HardDrive, MonitorSmartphone, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import {
  activatePendingServiceWorker,
  clearAllCaches,
  detectPushCapability,
  getActiveSubscription,
  getInstallStatus,
  getNotificationPermission,
  isIOS,
  sendTestPush,
  subscribeUserToPush,
  triggerInstallPrompt,
  unsubscribeUserFromPush,
} from '@/lib/pwa';
import { toast } from '@/stores/notification-store';

export function PWAStatusCard() {
  const [installStatus, setInstallStatus] = useState(() => getInstallStatus());
  const [pushSubscribed, setPushSubscribed] = useState(false);
  const [permission, setPermission] = useState<NotificationPermission | 'unavailable'>('unavailable');
  const [busy, setBusy] = useState(false);
  const [cap] = useState(() => (typeof window !== 'undefined' ? detectPushCapability() : null));

  // 초기 상태 동기화
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const sub = await getActiveSubscription().catch(() => null);
      if (cancelled) return;
      setPushSubscribed(!!sub);
      setPermission(getNotificationPermission());
      setInstallStatus(getInstallStatus());
    })();
    const onFocus = () => {
      setInstallStatus(getInstallStatus());
      setPermission(getNotificationPermission());
    };
    window.addEventListener('focus', onFocus);
    return () => {
      cancelled = true;
      window.removeEventListener('focus', onFocus);
    };
  }, []);

  const handleTogglePush = async (next: boolean) => {
    setBusy(true);
    try {
      if (next) {
        const res = await subscribeUserToPush({ requestPermissionIfNeeded: true });
        if (res.ok) {
          toast.success('푸시 알림이 활성화되었습니다.');
          setPushSubscribed(true);
          setPermission(getNotificationPermission());
        } else if (res.reason === 'PERMISSION_DENIED') {
          toast.warning('알림 권한이 거부되었습니다.', '브라우저/OS 설정에서 허용해주세요.');
        } else if (res.reason === 'NOT_STANDALONE') {
          toast.info('iOS 는 홈 화면에 추가 후 사용 가능합니다.');
        } else if (res.reason === 'NO_VAPID_KEY') {
          toast.warning('서버 VAPID 키가 설정되지 않았습니다.');
        } else {
          toast.danger('푸시 활성화 실패', res.error || res.reason);
        }
      } else {
        const ok = await unsubscribeUserFromPush();
        if (ok) {
          toast.success('푸시 알림을 해제했습니다.');
          setPushSubscribed(false);
        } else {
          toast.danger('푸시 해제 실패');
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const handleInstall = async () => {
    setBusy(true);
    try {
      const result = await triggerInstallPrompt();
      if (result === 'accepted') {
        toast.success('설치되었습니다.');
        setInstallStatus(getInstallStatus());
      } else if (result === 'unavailable') {
        toast.info(
          isIOS()
            ? 'Safari 공유 메뉴 → 홈 화면에 추가를 선택해주세요.'
            : '현재 브라우저에서는 설치 프롬프트가 준비되지 않았습니다.',
        );
      }
    } finally {
      setBusy(false);
    }
  };

  const handleTest = async () => {
    setBusy(true);
    try {
      const res = await sendTestPush();
      if (res.ok) toast.success('테스트 푸시를 발송했습니다.');
      else toast.danger('테스트 푸시 실패', res.error);
    } finally {
      setBusy(false);
    }
  };

  const handleClearCache = async () => {
    setBusy(true);
    try {
      const ok = await clearAllCaches();
      if (ok) toast.success('캐시를 정리했습니다.', '다음 진입 시 최신 자산이 로드됩니다.');
      else toast.warning('일부 캐시 정리 실패');
    } finally {
      setBusy(false);
    }
  };

  const handleUpdate = async () => {
    setBusy(true);
    try {
      await activatePendingServiceWorker();
      toast.info('새 버전을 적용합니다…');
    } finally {
      setBusy(false);
    }
  };

  const pushSupported = cap?.level === 'full';

  return (
    <Card>
      <Card.Header
        title={
          <span className="row items-center gap-2">
            <MonitorSmartphone className="h-4 w-4" /> PWA · 설치와 알림
          </span>
        }
      />
      <Card.Body className="stack gap-4">
        {/* 설치 상태 */}
        <div className="row items-center justify-between">
          <div>
            <p className="text-strong fw-medium">앱 설치 상태</p>
            <p className="text-subtle text-xs">
              홈 화면에 추가하면 브라우저 UI 없이 standalone 모드로 실행됩니다.
            </p>
          </div>
          <div className="row items-center gap-2">
            {installStatus.standalone ? (
              <Badge variant="success" dot>설치됨 (Standalone)</Badge>
            ) : installStatus.installed ? (
              <Badge variant="info">설치 완료</Badge>
            ) : installStatus.promptAvailable ? (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<Download size={14} />}
                onClick={handleInstall}
                disabled={busy}
              >
                설치
              </Button>
            ) : (
              <Badge variant="warning">{isIOS() ? '공유→홈에 추가' : '미설치'}</Badge>
            )}
          </div>
        </div>

        {/* 푸시 알림 */}
        <div className="row items-center justify-between">
          <div>
            <p className="text-strong fw-medium row items-center gap-2">
              <BellRing className="h-4 w-4" /> 푸시 알림
            </p>
            <p className="text-subtle text-xs">
              {pushSupported
                ? `브라우저에서 직접 알림을 받습니다. 권한: ${permission}`
                : (cap?.reason ?? '현재 환경은 Web Push 를 지원하지 않습니다.')}
            </p>
          </div>
          <div className="row items-center gap-2">
            <Switch
              checked={pushSubscribed}
              onChange={handleTogglePush}
              disabled={!pushSupported || busy || permission === 'denied'}
              ariaLabel="푸시 알림 토글"
            />
          </div>
        </div>

        {/* 테스트 발송 */}
        {pushSubscribed && (
          <div className="row items-center justify-between">
            <div>
              <p className="text-strong fw-medium">테스트 발송</p>
              <p className="text-subtle text-xs">서버에서 테스트 알림을 1건 발송합니다.</p>
            </div>
            <Button variant="outline" size="sm" onClick={handleTest} disabled={busy}>
              테스트 푸시
            </Button>
          </div>
        )}

        {/* 캐시 정리 */}
        <div className="row items-center justify-between">
          <div>
            <p className="text-strong fw-medium row items-center gap-2">
              <HardDrive className="h-4 w-4" /> 캐시 정리
            </p>
            <p className="text-subtle text-xs">
              Service Worker 가 저장한 정적 자산 / API 응답 캐시를 모두 비웁니다.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={handleClearCache} disabled={busy}>
            캐시 비우기
          </Button>
        </div>

        {/* 새 버전 강제 적용 */}
        <div className="row items-center justify-between">
          <div>
            <p className="text-strong fw-medium row items-center gap-2">
              <RefreshCw className="h-4 w-4" /> 새 버전 적용
            </p>
            <p className="text-subtle text-xs">
              대기 중인 새 Service Worker 버전을 즉시 활성화하고 새로고침합니다.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={handleUpdate} disabled={busy}>
            업데이트
          </Button>
        </div>
      </Card.Body>
    </Card>
  );
}
