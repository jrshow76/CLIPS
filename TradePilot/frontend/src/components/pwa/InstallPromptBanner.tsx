'use client';

/**
 * 홈 화면 추가 권장 배너.
 * - Chrome/Edge/Android: `beforeinstallprompt` 가용 시 prompt() 호출 가능 버튼
 * - iOS Safari: "공유 → 홈 화면에 추가" 텍스트 가이드 (직접 prompt 불가)
 * - 거절 시 14일간 미노출 (localStorage)
 *
 * 노출 시점: 사용자가 최소 1회 페이지 이동을 한 후 5초 뒤 표시 (즉시 표시 X)
 */

import { Download, Share, X } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  dismissInstallPrompt,
  isIOS,
  isStandalone,
  onInstallPromptChange,
  shouldShowBanner,
  triggerInstallPrompt,
} from '@/lib/pwa';

export function InstallPromptBanner() {
  const [visible, setVisible] = useState(false);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    if (isStandalone()) return;
    let cancelled = false;
    const check = () => {
      if (cancelled) return;
      setVisible(shouldShowBanner());
    };
    // 5초 후 진입 (UX: 첫 진입 직후 방해 금지)
    const t = window.setTimeout(check, 5000);
    const unsub = onInstallPromptChange(check);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
      unsub();
    };
  }, []);

  if (!visible) return null;

  const ios = isIOS();

  const handleInstall = async () => {
    setInstalling(true);
    try {
      const result = await triggerInstallPrompt();
      if (result === 'unavailable' && !ios) {
        // 일부 브라우저는 deferred prompt 가 아직 없음 — 닫지 않고 안내만
      }
      setVisible(false);
    } finally {
      setInstalling(false);
    }
  };

  const handleDismiss = () => {
    dismissInstallPrompt();
    setVisible(false);
  };

  return (
    <div
      role="region"
      aria-label="앱 설치 안내"
      className="install-banner"
      style={{
        position: 'fixed',
        left: '12px',
        right: '12px',
        bottom: '12px',
        zIndex: 50,
        background: 'var(--color-bg-elev, #131a26)',
        border: '1px solid var(--color-border, #1f2937)',
        borderRadius: '14px',
        padding: '14px 16px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
        display: 'flex',
        gap: '12px',
        alignItems: 'flex-start',
        maxWidth: '560px',
        margin: '0 auto',
      }}
    >
      <div aria-hidden="true" style={{ flex: '0 0 auto', paddingTop: 2 }}>
        {ios ? <Share size={20} /> : <Download size={20} />}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, fontWeight: 700, fontSize: 14 }}>
          {ios ? 'TradePilot 을 홈 화면에 추가하세요' : 'TradePilot 앱으로 설치하시겠어요?'}
        </p>
        <p style={{ margin: '4px 0 10px', fontSize: 12, color: 'var(--color-text-muted, #94a3b8)' }}>
          {ios
            ? 'Safari 하단의 공유 버튼을 누른 뒤 “홈 화면에 추가”를 선택하세요. iOS 16.4 이상에서는 푸시 알림도 받을 수 있습니다.'
            : '홈 화면에서 바로 실행하고, 오프라인 셸·푸시 알림을 사용할 수 있습니다.'}
        </p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {!ios && (
            <Button variant="primary" size="sm" onClick={handleInstall} loading={installing}>
              지금 설치
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleDismiss}>
            나중에
          </Button>
        </div>
      </div>
      <button
        type="button"
        aria-label="배너 닫기"
        onClick={handleDismiss}
        style={{
          flex: '0 0 auto',
          background: 'transparent',
          border: 0,
          padding: 4,
          cursor: 'pointer',
          color: 'var(--color-text-muted, #94a3b8)',
        }}
      >
        <X size={16} />
      </button>
    </div>
  );
}
