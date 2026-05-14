'use client';

/**
 * 네트워크 오프라인 상태 표시 인디케이터.
 * 헤더 또는 상태바 영역에 마운트해 사용자에게 오프라인을 시각적으로 알린다.
 */

import { CloudOff, Wifi } from 'lucide-react';
import { useEffect, useState } from 'react';

export interface OfflineIndicatorProps {
  /** 인라인 표시 (헤더 배지) vs 토스트 형 (하단 띠) */
  variant?: 'badge' | 'toast';
  /** 온라인 상태일 때도 짧게 노출(복귀 알림) */
  showOnlineRestore?: boolean;
}

export function OfflineIndicator({
  variant = 'badge',
  showOnlineRestore = true,
}: OfflineIndicatorProps) {
  const [online, setOnline] = useState(true);
  const [justRestored, setJustRestored] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    setOnline(navigator.onLine);
    const goOnline = () => {
      setOnline(true);
      if (showOnlineRestore) {
        setJustRestored(true);
        window.setTimeout(() => setJustRestored(false), 3000);
      }
    };
    const goOffline = () => setOnline(false);
    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, [showOnlineRestore]);

  if (online && !justRestored) return null;

  if (variant === 'badge') {
    return (
      <span
        role="status"
        aria-live="polite"
        title={online ? '온라인 복귀' : '오프라인 상태'}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 8px',
          borderRadius: 999,
          background: online ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
          border: `1px solid ${online ? 'rgba(34,197,94,0.35)' : 'rgba(239,68,68,0.4)'}`,
          color: online ? '#86efac' : '#fca5a5',
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        {online ? <Wifi size={12} /> : <CloudOff size={12} />}
        {online ? '온라인 복귀' : '오프라인'}
      </span>
    );
  }

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        left: '50%',
        bottom: 12,
        transform: 'translateX(-50%)',
        zIndex: 60,
        background: online ? 'rgba(22,163,74,0.95)' : 'rgba(220,38,38,0.95)',
        color: '#fff',
        padding: '10px 16px',
        borderRadius: 12,
        fontSize: 13,
        fontWeight: 600,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        boxShadow: '0 6px 18px rgba(0,0,0,0.35)',
      }}
    >
      {online ? <Wifi size={14} /> : <CloudOff size={14} />}
      {online ? '연결이 복구되었습니다.' : '오프라인 — 일부 기능이 제한됩니다.'}
    </div>
  );
}
