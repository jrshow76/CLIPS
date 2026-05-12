'use client';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Field, Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { useUpdateSettings, useUserSettings } from '@/lib/api/queries/settings';
import { useState, useEffect } from 'react';
import { toast } from '@/stores/notification-store';

export default function SettingsPage() {
  const settings = useUserSettings();
  const update = useUpdateSettings();

  const [notifySignal, setNotifySignal] = useState(true);
  const [notifyFill, setNotifyFill] = useState(true);
  const [buyLimit, setBuyLimit] = useState(0);
  const [lossLimit, setLossLimit] = useState(0);

  useEffect(() => {
    if (settings.data) {
      setNotifySignal(settings.data.notify_on_signal);
      setNotifyFill(settings.data.notify_on_fill);
      setBuyLimit(settings.data.daily_buy_limit);
      setLossLimit(settings.data.daily_loss_limit);
    }
  }, [settings.data]);

  async function onSave() {
    await update.mutateAsync({
      notify_on_signal: notifySignal,
      notify_on_fill: notifyFill,
      daily_buy_limit: buyLimit,
      daily_loss_limit: lossLimit,
    });
  }

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>설정</h1>
          <p>알림, 한도, 매매 모드 설정을 관리합니다.</p>
        </div>
      </div>

      {settings.isLoading && <Skeleton height={300} />}

      {settings.data && (
        <div className="grid-cols-2">
          <Card>
            <Card.Header title="알림" />
            <Card.Body className="stack gap-4">
              <div className="row items-center justify-between">
                <div>
                  <p className="text-strong fw-medium">시그널 발생 알림</p>
                  <p className="text-subtle text-xs">매수/매도 시그널이 생성되면 알림을 받습니다.</p>
                </div>
                <Switch checked={notifySignal} onChange={setNotifySignal} ariaLabel="시그널 알림" />
              </div>
              <div className="row items-center justify-between">
                <div>
                  <p className="text-strong fw-medium">체결 알림</p>
                  <p className="text-subtle text-xs">주문이 체결되면 알림을 받습니다.</p>
                </div>
                <Switch checked={notifyFill} onChange={setNotifyFill} ariaLabel="체결 알림" />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Header title="리스크 한도" />
            <Card.Body className="stack gap-4">
              <Field label="일일 매수 한도 (원)">
                <Input type="number" value={buyLimit} onChange={(e) => setBuyLimit(Number(e.target.value))} />
              </Field>
              <Field label="일일 손실 한도 (원, 음수)">
                <Input type="number" value={lossLimit} onChange={(e) => setLossLimit(Number(e.target.value))} />
              </Field>
              <Button
                variant="primary"
                onClick={() => onSave().catch(() => toast.danger('저장 실패'))}
                loading={update.isPending}
              >
                저장
              </Button>
            </Card.Body>
          </Card>
        </div>
      )}
    </>
  );
}
