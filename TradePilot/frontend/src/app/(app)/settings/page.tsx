'use client';

import { Bell, KeyRound, Plug, Shield, SlidersHorizontal, Sun, User2 } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

import { Badge } from '@/components/ui/badge';
import { Banner } from '@/components/ui/banner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Field, Input } from '@/components/ui/input';
import { RadioGroup } from '@/components/ui/radio';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Tabs } from '@/components/ui/tabs';
import { useUpdateSettings, useUserSettings } from '@/lib/api/queries/settings';
import { passwordSchema } from '@/lib/forms/zod-schemas';
import { ROUTES } from '@/lib/constants';
import { z } from 'zod';
import { useAuthStore } from '@/stores/auth-store';
import { useTradeModeStore } from '@/stores/trade-mode-store';
import { useThemeStore } from '@/stores/theme-store';
import { zodResolver } from '@/lib/forms/zod-resolver';
import { toast } from '@/stores/notification-store';

type Tab = 'account' | 'security' | 'notify' | 'limits' | 'creon' | 'appearance';

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>('account');

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>설정</h1>
          <p>계정, 보안, 알림, 매매한도, 외관을 한곳에서 관리합니다.</p>
        </div>
      </div>

      <Tabs<Tab>
        value={tab}
        onChange={setTab}
        items={[
          { value: 'account', label: '계정' },
          { value: 'security', label: '보안' },
          { value: 'notify', label: '알림' },
          { value: 'limits', label: '매매한도' },
          { value: 'creon', label: '크레온' },
          { value: 'appearance', label: '외관' },
        ]}
      />

      <div className="mt-4">
        {tab === 'account' && <AccountTab />}
        {tab === 'security' && <SecurityTab />}
        {tab === 'notify' && <NotifyTab />}
        {tab === 'limits' && <LimitsTab />}
        {tab === 'creon' && <CreonTab />}
        {tab === 'appearance' && <AppearanceTab />}
      </div>
    </>
  );
}

/* -------------------- 계정 탭 -------------------- */
const accountSchema = z.object({
  nickname: z.string().min(2, '닉네임은 2자 이상').max(16, '닉네임은 16자 이하'),
  phone: z.string().optional(),
});
type AccountForm = z.infer<typeof accountSchema>;

function AccountTab() {
  const user = useAuthStore((s) => s.user);
  const form = useForm<AccountForm>({
    resolver: zodResolver<AccountForm>(accountSchema),
    defaultValues: { nickname: user?.nickname ?? '', phone: user?.phone ?? '' },
  });
  const { register, handleSubmit, formState: { errors, isSubmitting } } = form;

  return (
    <Card>
      <Card.Header title="계정 정보" />
      <form onSubmit={handleSubmit(async () => { await new Promise((r) => setTimeout(r, 300)); toast.success('계정 정보가 저장되었습니다.'); })} noValidate>
        <Card.Body className="stack gap-4">
          <Field label="이메일">
            <Input value={user?.email ?? '-'} disabled />
          </Field>
          <Field label="권한">
            <Badge variant="info">{user?.role ?? '-'}</Badge>
          </Field>
          <Field label="닉네임" required error={errors.nickname?.message}>
            <Input {...register('nickname')} leftIcon={<User2 className="h-4 w-4" />} />
          </Field>
          <Field label="휴대폰" error={errors.phone?.message}>
            <Input placeholder="010-0000-0000" {...register('phone')} />
          </Field>
        </Card.Body>
        <Card.Footer>
          <div className="row gap-2 justify-end">
            <Button type="submit" variant="primary" loading={isSubmitting}>저장</Button>
          </div>
        </Card.Footer>
      </form>
    </Card>
  );
}

/* -------------------- 보안 탭 -------------------- */
const securitySchema = z
  .object({
    current_password: z.string().min(1, '현재 비밀번호를 입력해주세요.'),
    new_password: passwordSchema,
    new_password_confirm: z.string().min(1, '새 비밀번호 확인을 입력해주세요.'),
  })
  .refine((v) => v.new_password === v.new_password_confirm, {
    path: ['new_password_confirm'],
    message: '비밀번호가 일치하지 않습니다.',
  });
type SecurityForm = z.infer<typeof securitySchema>;

function SecurityTab() {
  const mode = useTradeModeStore((s) => s.mode);
  const openLive = useTradeModeStore((s) => s.openLiveConfirm);
  const setMode = useTradeModeStore((s) => s.setMode);
  const form = useForm<SecurityForm>({
    resolver: zodResolver<SecurityForm>(securitySchema),
    defaultValues: { current_password: '', new_password: '', new_password_confirm: '' },
  });

  return (
    <div className="grid-cols-2">
      <Card>
        <Card.Header title="비밀번호 변경" />
        <form onSubmit={form.handleSubmit(async () => { await new Promise((r) => setTimeout(r, 300)); toast.success('비밀번호가 변경되었습니다.'); })} noValidate>
          <Card.Body className="stack gap-3">
            <Field label="현재 비밀번호" required error={form.formState.errors.current_password?.message}>
              <Input type="password" leftIcon={<KeyRound className="h-4 w-4" />} {...form.register('current_password')} />
            </Field>
            <Field label="새 비밀번호" required error={form.formState.errors.new_password?.message}>
              <Input type="password" leftIcon={<KeyRound className="h-4 w-4" />} {...form.register('new_password')} />
            </Field>
            <Field label="새 비밀번호 확인" required error={form.formState.errors.new_password_confirm?.message}>
              <Input type="password" leftIcon={<KeyRound className="h-4 w-4" />} {...form.register('new_password_confirm')} />
            </Field>
          </Card.Body>
          <Card.Footer>
            <div className="row gap-2 justify-end">
              <Button type="submit" variant="primary" loading={form.formState.isSubmitting}>변경</Button>
            </div>
          </Card.Footer>
        </form>
      </Card>

      <Card>
        <Card.Header
          title={<span className="row items-center gap-2"><Shield className="h-4 w-4" /> 매매 모드</span>}
        />
        <Card.Body className="stack gap-4">
          <Banner variant={mode === 'LIVE' ? 'live' : 'info'}>
            현재 모드: <Badge variant={mode === 'LIVE' ? 'live' : 'sim'} dot>{mode}</Badge>
            {mode === 'LIVE' ? ' — 실제 주문이 전송됩니다.' : ' — 가상 자금으로 안전하게 거래합니다.'}
          </Banner>
          <div className="row gap-2">
            <Button
              variant={mode === 'SIM' ? 'primary' : 'outline'}
              onClick={() => setMode('SIM', { confirmed: true })}
              disabled={mode === 'SIM'}
            >
              SIM으로 전환
            </Button>
            <Button
              variant={mode === 'LIVE' ? 'danger' : 'outline'}
              onClick={() => openLive()}
              disabled={mode === 'LIVE'}
            >
              LIVE로 전환
            </Button>
          </div>
          <p className="text-xs text-subtle">LIVE 전환은 OTP 인증 + 권한 확인이 필요합니다.</p>
          <Link href={`${ROUTES.OTP}?purpose=live`} className="text-sm" style={{ color: 'var(--color-brand-300)' }}>
            OTP 화면 직접 열기 →
          </Link>
        </Card.Body>
      </Card>
    </div>
  );
}

/* -------------------- 알림 탭 -------------------- */
function NotifyTab() {
  const settings = useUserSettings();
  const update = useUpdateSettings();
  const [notifySignal, setNotifySignal] = useState(true);
  const [notifyFill, setNotifyFill] = useState(true);
  const [channel, setChannel] = useState<'WEB' | 'EMAIL' | 'PUSH'>('WEB');

  useEffect(() => {
    if (settings.data) {
      setNotifySignal(settings.data.notify_on_signal);
      setNotifyFill(settings.data.notify_on_fill);
    }
  }, [settings.data]);

  if (settings.isLoading) return <Skeleton height={200} />;

  return (
    <Card>
      <Card.Header title={<span className="row items-center gap-2"><Bell className="h-4 w-4" /> 알림 설정</span>} />
      <Card.Body className="stack gap-4">
        <div className="row items-center justify-between">
          <div>
            <p className="text-strong fw-medium">시그널 발생 알림</p>
            <p className="text-subtle text-xs">매수/매도 시그널이 생성되면 알림을 받습니다.</p>
          </div>
          <Switch checked={notifySignal} onChange={setNotifySignal} />
        </div>
        <div className="row items-center justify-between">
          <div>
            <p className="text-strong fw-medium">체결 알림</p>
            <p className="text-subtle text-xs">주문이 체결되면 알림을 받습니다.</p>
          </div>
          <Switch checked={notifyFill} onChange={setNotifyFill} />
        </div>
        <Field label="기본 알림 채널">
          <RadioGroup<'WEB' | 'EMAIL' | 'PUSH'>
            name="channel"
            value={channel}
            onChange={setChannel}
            options={[
              { value: 'WEB', label: '웹 알림' },
              { value: 'EMAIL', label: '이메일' },
              { value: 'PUSH', label: '모바일 푸시' },
            ]}
          />
        </Field>
      </Card.Body>
      <Card.Footer>
        <div className="row gap-2 justify-end">
          <Button
            variant="primary"
            loading={update.isPending}
            onClick={() => update.mutate({ notify_on_signal: notifySignal, notify_on_fill: notifyFill })}
          >
            저장
          </Button>
        </div>
      </Card.Footer>
    </Card>
  );
}

/* -------------------- 매매한도 탭 -------------------- */
function LimitsTab() {
  return (
    <Card>
      <Card.Header title={<span className="row items-center gap-2"><SlidersHorizontal className="h-4 w-4" /> 매매한도</span>} />
      <Card.Body>
        <p className="text-sm text-muted mb-3">
          상세 한도 설정과 사용 현황은 별도 페이지에서 관리합니다.
        </p>
        <Link href={ROUTES.AUTO_TRADING_LIMITS}>
          <Button variant="primary">한도 설정 페이지 열기 →</Button>
        </Link>
      </Card.Body>
    </Card>
  );
}

/* -------------------- 크레온 탭 -------------------- */
function CreonTab() {
  return (
    <Card>
      <Card.Header title={<span className="row items-center gap-2"><Plug className="h-4 w-4" /> 크레온 게이트웨이</span>} />
      <Card.Body>
        <p className="text-sm text-muted mb-3">크레온 연결 상태와 테스트는 전용 페이지에서 관리합니다.</p>
        <Link href={ROUTES.SETTINGS_CREON}>
          <Button variant="primary">크레온 설정 →</Button>
        </Link>
      </Card.Body>
    </Card>
  );
}

/* -------------------- 외관 탭 -------------------- */
function AppearanceTab() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  return (
    <Card>
      <Card.Header title={<span className="row items-center gap-2"><Sun className="h-4 w-4" /> 테마</span>} />
      <Card.Body className="stack gap-4">
        <RadioGroup<'light' | 'dark'>
          name="theme"
          value={theme}
          onChange={setTheme}
          options={[
            { value: 'light', label: '라이트' },
            { value: 'dark', label: '다크' },
          ]}
        />
        <p className="text-xs text-subtle">변경 즉시 반영됩니다.</p>
      </Card.Body>
    </Card>
  );
}
