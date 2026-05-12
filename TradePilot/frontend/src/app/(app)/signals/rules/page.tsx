'use client';

import { Pencil, Plus, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { EmptyState } from '@/components/ui/empty-state';
import { Field, Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { DataTable, type Column } from '@/components/ui/table';
import { useDeleteSignalRule, useSaveSignalRule, useSignalRules } from '@/lib/api/queries/signal-rules';
import { signalRuleFormSchema, type SignalRuleForm } from '@/lib/forms/zod-schemas';
import { zodResolver } from '@/lib/forms/zod-resolver';
import { ROUTES } from '@/lib/constants';
import type { MockSignalRule } from '@/lib/mocks/data';

export default function SignalRulesPage() {
  const rules = useSignalRules();
  const save = useSaveSignalRule();
  const remove = useDeleteSignalRule();

  const [editing, setEditing] = useState<MockSignalRule | null>(null);
  const [open, setOpen] = useState(false);

  const form = useForm<SignalRuleForm>({
    resolver: zodResolver<SignalRuleForm>(signalRuleFormSchema),
    defaultValues: {
      name: '',
      indicator: 'RSI',
      operator: '<',
      value: 30,
      enabled: true,
      notify_channel: 'WEB',
    },
  });
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = form;

  function startNew() {
    setEditing(null);
    reset({ name: '', indicator: 'RSI', operator: '<', value: 30, enabled: true, notify_channel: 'WEB' });
    setOpen(true);
  }

  function startEdit(rule: MockSignalRule) {
    setEditing(rule);
    reset({
      name: rule.name,
      indicator: rule.indicator,
      operator: rule.operator,
      value: rule.value,
      enabled: rule.enabled,
      notify_channel: rule.notify_channel,
    });
    setOpen(true);
  }

  const onSubmit = handleSubmit(async (values) => {
    await save.mutateAsync({ id: editing?.id, ...values });
    setOpen(false);
  });

  const columns: Column<MockSignalRule>[] = [
    { key: 'name', header: '규칙명', cell: (r) => <span className="fw-semibold">{r.name}</span>, sortAccessor: 'name' },
    { key: 'indicator', header: '지표', cell: (r) => <Badge variant="info">{r.indicator}</Badge> },
    { key: 'op', header: '조건', cell: (r) => `${r.operator} ${r.value}` },
    {
      key: 'channel',
      header: '알림 채널',
      cell: (r) => ({ WEB: '웹', EMAIL: '이메일', PUSH: '푸시' }[r.notify_channel]),
    },
    {
      key: 'enabled',
      header: '활성',
      cell: (r) => (
        <Switch
          checked={r.enabled}
          onChange={(v) => save.mutate({ ...r, enabled: v })}
        />
      ),
    },
    {
      key: 'action',
      header: '',
      align: 'right',
      cell: (r) => (
        <div className="row gap-1 justify-end">
          <Button variant="ghost" size="icon" onClick={() => startEdit(r)} aria-label="편집">
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              if (window.confirm(`"${r.name}" 규칙을 삭제하시겠습니까?`)) remove.mutate(r.id);
            }}
            aria-label="삭제"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>알림 규칙</h1>
          <p>지표 임계값으로 알림 규칙을 만들고 채널을 지정합니다.</p>
        </div>
        <div className="row gap-2">
          <Link href={ROUTES.SIGNALS}><Button variant="outline">← 시그널 목록</Button></Link>
          <Button variant="primary" leftIcon={<Plus className="h-4 w-4" />} onClick={startNew}>
            새 규칙
          </Button>
        </div>
      </div>

      {rules.isLoading && <Skeleton height={200} />}
      {rules.isError && <ErrorCard message="알림 규칙을 불러올 수 없습니다." />}
      {rules.data && rules.data.length === 0 && (
        <EmptyState
          title="등록된 알림 규칙이 없습니다."
          description="자주 보는 지표 조건을 등록하여 알림을 받아보세요."
          action={<Button variant="primary" onClick={startNew}>첫 규칙 만들기</Button>}
        />
      )}

      {rules.data && rules.data.length > 0 && (
        <Card>
          <Card.Body className="p-0">
            <DataTable columns={columns} data={rules.data} rowKey={(r) => r.id} />
          </Card.Body>
        </Card>
      )}

      {/* 신규/편집 모달 */}
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={editing ? '규칙 편집' : '새 알림 규칙'}
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>취소</Button>
            <Button variant="primary" onClick={onSubmit} loading={isSubmitting || save.isPending}>
              저장
            </Button>
          </>
        }
      >
        <form onSubmit={onSubmit} className="stack gap-3" noValidate>
          <Field label="규칙명" required error={errors.name?.message}>
            <Input {...register('name')} placeholder="예: 셀트리온 RSI 과매도" />
          </Field>
          <div className="row gap-2">
            <Field label="지표" required error={errors.indicator?.message} className="flex-1">
              <Select {...register('indicator')}>
                <option value="RSI">RSI</option>
                <option value="MACD">MACD</option>
                <option value="MA5">MA5</option>
                <option value="MA20">MA20</option>
                <option value="MA60">MA60</option>
                <option value="BBANDS_UPPER">볼린저 상단</option>
                <option value="BBANDS_LOWER">볼린저 하단</option>
              </Select>
            </Field>
            <Field label="연산자" required error={errors.operator?.message} className="flex-1">
              <Select {...register('operator')}>
                <option value="<">&lt;</option>
                <option value="<=">≤</option>
                <option value="=">=</option>
                <option value=">=">≥</option>
                <option value=">">&gt;</option>
                <option value="CROSS_UP">CROSS UP</option>
                <option value="CROSS_DOWN">CROSS DOWN</option>
              </Select>
            </Field>
          </div>
          <Field label="기준값" required error={errors.value?.message}>
            <Input type="number" step="0.01" {...register('value', { valueAsNumber: true })} />
          </Field>
          <Field label="알림 채널" required error={errors.notify_channel?.message}>
            <Select {...register('notify_channel')}>
              <option value="WEB">웹 알림</option>
              <option value="EMAIL">이메일</option>
              <option value="PUSH">모바일 푸시</option>
            </Select>
          </Field>
          <Field label="활성 상태" hint="등록 후 즉시 활성화됩니다.">
            <div className="row items-center gap-2">
              <Switch
                checked={form.watch('enabled')}
                onChange={(v) => form.setValue('enabled', v)}
              />
              <span className="text-sm">활성</span>
            </div>
          </Field>
        </form>
      </Modal>
    </>
  );
}
