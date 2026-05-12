'use client';

import { AlertTriangle } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Field, Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { canTradeLive, useAuthStore } from '@/stores/auth-store';
import { useTradeModeStore } from '@/stores/trade-mode-store';
import { useSwitchTradeMode } from '@/lib/api/queries/settings';
import { toast } from '@/stores/notification-store';

/**
 * SIM ↔ LIVE 전환 확인 모달 (2단계).
 * 1) 위험 안내 + 권한 확인
 * 2) "LIVE" 텍스트 입력 검증 (오타/실수 방지)
 *
 * 흐름:
 *   TradeModeToggle.click('LIVE') → store.setMode('LIVE') (confirmed=false)
 *     → store.liveConfirmOpen = true
 *     → 이 모달이 열림 → 확인 통과 시 useSwitchTradeMode → setMode('LIVE', {confirmed:true})
 */
export function LiveModeModal() {
  const open = useTradeModeStore((s) => s.liveConfirmOpen);
  const close = useTradeModeStore((s) => s.closeLiveConfirm);
  const user = useAuthStore((s) => s.user);
  const switchMode = useSwitchTradeMode();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);

  const allowed = canTradeLive(user);
  const matched = text.trim() === 'LIVE';

  async function onConfirm() {
    if (!allowed) {
      toast.warning('실거래 사용 권한이 없습니다.', '관리자에게 문의해주세요. (E0016)');
      return;
    }
    if (!matched) return;
    setBusy(true);
    try {
      await switchMode.mutateAsync('LIVE');
      setText('');
      close();
    } finally {
      setBusy(false);
    }
  }

  function onCancel() {
    setText('');
    close();
  }

  return (
    <Modal
      open={open}
      onClose={onCancel}
      danger
      title="실거래(LIVE) 모드 전환"
      footer={
        <>
          <Button variant="ghost" onClick={onCancel} disabled={busy}>
            취소
          </Button>
          <Button variant="danger" disabled={!matched || !allowed || busy} loading={busy} onClick={onConfirm}>
            LIVE로 전환
          </Button>
        </>
      }
    >
      <div className="stack gap-4">
        <div className="row gap-3 items-start">
          <AlertTriangle className="text-danger mt-1 h-5 w-5 flex-none" />
          <div className="stack gap-1">
            <p className="text-strong fw-semibold">
              실거래 모드 진입 시 모든 주문이 실제 증권사 계좌로 전송됩니다.
            </p>
            <p className="text-muted text-sm">
              주문 한도 / 일일 손실 한도가 즉시 적용되며, 비상정지(Kill Switch)는 SIM/LIVE 어디서나 동일하게 동작합니다.
            </p>
          </div>
        </div>

        {!allowed && (
          <div className="error-card">
            <div>
              <p className="error-card__title">실거래 권한이 없습니다.</p>
              <p className="error-card__msg">
                LIVE 모드는 ROLE_TRADER_PRO 이상 권한이 필요합니다. (E0016)
              </p>
            </div>
          </div>
        )}

        <Field
          label='동의를 위해 "LIVE"를 입력하세요.'
          hint='대소문자 구분, 영문 4글자'
        >
          <Input value={text} onChange={(e) => setText(e.target.value)} placeholder="LIVE" autoFocus />
        </Field>
      </div>
    </Modal>
  );
}
