'use client';

/**
 * 알림 권한 요청 모달.
 * - 사용자 명시 동작(설정 토글, 첫 로그인 후 안내) 시 호출.
 * - 권한이 'default' 일 때만 표시. 'denied' 면 OS 설정으로 안내.
 */

import { Bell, BellOff, BellRing } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal';
import {
  detectPushCapability,
  getNotificationPermission,
  subscribeUserToPush,
} from '@/lib/pwa';
import { toast } from '@/stores/notification-store';

interface Props {
  open: boolean;
  onClose: () => void;
  onResult?: (state: 'granted' | 'denied' | 'unsupported' | 'failed') => void;
}

export function NotificationPermissionPrompt({ open, onClose, onResult }: Props) {
  const [working, setWorking] = useState(false);
  const [permission, setPermission] = useState<NotificationPermission | 'unavailable'>('unavailable');
  const cap = typeof window !== 'undefined' ? detectPushCapability() : null;

  useEffect(() => {
    if (open) setPermission(getNotificationPermission());
  }, [open]);

  const handleAllow = async () => {
    setWorking(true);
    try {
      const result = await subscribeUserToPush({ requestPermissionIfNeeded: true });
      if (result.ok) {
        toast.success('알림이 활성화되었습니다.');
        onResult?.('granted');
        onClose();
      } else if (result.reason === 'PERMISSION_DENIED') {
        toast.warning('알림 권한이 거부되었습니다. 브라우저/OS 설정에서 다시 허용할 수 있습니다.');
        onResult?.('denied');
      } else if (result.reason === 'NOT_STANDALONE') {
        toast.info('iOS 에서는 먼저 홈 화면에 추가해주세요.');
        onResult?.('unsupported');
      } else {
        toast.danger('알림 등록 실패', result.error || result.reason);
        onResult?.('failed');
      }
    } finally {
      setWorking(false);
    }
  };

  if (!open) return null;

  const isDenied = permission === 'denied';
  const unsupported = cap?.level === 'unsupported';

  return (
    <Modal open={open} onClose={onClose} title="푸시 알림 받기">
      <div className="stack gap-3">
        <div className="row items-start gap-3">
          <div aria-hidden style={{ flex: '0 0 auto', paddingTop: 2 }}>
            {isDenied ? <BellOff size={24} /> : <BellRing size={24} />}
          </div>
          <div>
            <p style={{ margin: 0, fontWeight: 600 }}>
              매매 시그널과 체결, 비상정지 알림을 실시간으로 받아보세요.
            </p>
            <p
              style={{
                margin: '6px 0 0',
                fontSize: 13,
                color: 'var(--color-text-muted, #94a3b8)',
                lineHeight: 1.6,
              }}
            >
              네트워크가 없어도 OS 알림센터로 전달되며, 앱이 닫혀 있어도 동작합니다.
              알림은 언제든 설정에서 끌 수 있습니다.
            </p>
          </div>
        </div>

        {unsupported && (
          <div
            role="alert"
            style={{
              background: 'rgba(239,68,68,0.12)',
              border: '1px solid rgba(239,68,68,0.35)',
              color: '#fca5a5',
              padding: '10px 12px',
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            현재 브라우저는 Web Push 를 지원하지 않습니다.
            {cap?.reason ? ` (${cap.reason})` : ''}
            <br />
            이메일/SMS 알림 채널로 대체 발송이 가능합니다.
          </div>
        )}

        {isDenied && (
          <div
            role="alert"
            style={{
              background: 'rgba(234,179,8,0.12)',
              border: '1px solid rgba(234,179,8,0.35)',
              color: '#fde68a',
              padding: '10px 12px',
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            브라우저가 이전에 알림을 차단했습니다. 주소창의 자물쇠 아이콘 →
            “사이트 설정” → “알림” 을 허용으로 변경 후 다시 시도해주세요.
          </div>
        )}

        <div className="row gap-2 justify-end">
          <Button variant="outline" onClick={onClose}>
            나중에
          </Button>
          <Button
            variant="primary"
            leftIcon={<Bell size={16} />}
            onClick={handleAllow}
            loading={working}
            disabled={unsupported || isDenied}
          >
            알림 허용
          </Button>
        </div>
      </div>
    </Modal>
  );
}
