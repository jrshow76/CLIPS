'use client';

import { Plus, Trash2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useFieldArray, useForm, type SubmitHandler } from 'react-hook-form';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Field, Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { StockSearchInput } from '@/components/forms/StockSearchInput';
import { useSaveStrategy } from '@/lib/api/queries/strategies';
import { ROUTES } from '@/lib/constants';
import { applyFieldErrors, toUserMessage } from '@/lib/forms/extract-field-errors';
import { strategyFormSchema, type StrategyForm } from '@/lib/forms/zod-schemas';
import { zodResolver } from '@/lib/forms/zod-resolver';
import { toast } from '@/stores/notification-store';
import type { Strategy } from '@/types/strategy';
import { useState } from 'react';

/**
 * 전략 작성/편집 폼.
 * - useFieldArray로 universe, rules, rule[].conditions 동적 관리.
 * - 저장 후 /auto-trading 으로 이동.
 */
export function StrategyForm({ initial, mode }: { initial?: Strategy; mode: 'new' | 'edit' }) {
  const router = useRouter();
  const save = useSaveStrategy();
  const [serverError, setServerError] = useState<string | null>(null);

  const form = useForm<StrategyForm>({
    resolver: zodResolver<StrategyForm>(strategyFormSchema),
    defaultValues: initial
      ? {
          name: initial.name,
          description: initial.description ?? '',
          universe: initial.universe,
          rules: initial.rules.map((r) => ({
            side: r.side,
            qty_mode: r.qty_mode,
            qty_value: r.qty_value,
            conditions: r.conditions,
          })),
          max_position_pct: initial.risk_limit?.max_position ?? 30,
          daily_loss_limit: initial.risk_limit?.daily_loss ?? -300_000,
        }
      : {
          name: '',
          description: '',
          universe: [],
          rules: [
            {
              side: 'BUY',
              qty_mode: 'PERCENT',
              qty_value: 10,
              conditions: [{ indicator: 'MA5', operator: 'CROSS_UP', value: 20 }],
            },
          ],
          max_position_pct: 30,
          daily_loss_limit: -300_000,
        },
  });

  const { register, handleSubmit, control, watch, setValue, setError, formState: { errors, isSubmitting } } = form;
  const rules = useFieldArray({ control, name: 'rules' });
  const universe = watch('universe');

  function addStock(code: string) {
    if (!universe.includes(code)) setValue('universe', [...universe, code]);
  }
  function removeStock(code: string) {
    setValue('universe', universe.filter((c) => c !== code));
  }

  const onSubmit: SubmitHandler<StrategyForm> = async (values) => {
    setServerError(null);
    try {
      await save.mutateAsync({
        id: initial?.id,
        name: values.name,
        description: values.description,
        universe: values.universe,
        rules: values.rules,
        risk_limit: {
          max_position: values.max_position_pct,
          daily_loss: values.daily_loss_limit,
        },
        status: initial?.status ?? 'DRAFT',
      });
      toast.success(mode === 'new' ? '전략이 생성되었습니다.' : '전략이 수정되었습니다.');
      router.push(ROUTES.AUTO_TRADING);
    } catch (err) {
      if (!applyFieldErrors<StrategyForm>(err, setError)) {
        setServerError(toUserMessage(err));
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="stack gap-4" noValidate>
      <Card>
        <Card.Header title="기본 정보" />
        <Card.Body className="stack gap-4">
          <Field label="전략명" required error={errors.name?.message}>
            <Input {...register('name')} placeholder="예: 골든크로스 5/20" />
          </Field>
          <Field label="설명" error={errors.description?.message}>
            <Textarea rows={3} {...register('description')} placeholder="전략 설명을 입력하세요" />
          </Field>
        </Card.Body>
      </Card>

      {/* 유니버스 */}
      <Card>
        <Card.Header
          title="대상 종목 (유니버스)"
          subtitle="자동매매가 적용될 종목을 추가하세요."
        />
        <Card.Body className="stack gap-3">
          <StockSearchInput onSelect={(s) => addStock(s.code)} placeholder="종목 추가" />
          <div className="row gap-2 flex-wrap">
            {universe.length === 0 && <span className="text-subtle text-sm">아직 추가된 종목이 없습니다.</span>}
            {universe.map((code) => (
              <Badge key={code} variant="default">
                <span className="row items-center gap-2">
                  {code}
                  <button
                    type="button"
                    onClick={() => removeStock(code)}
                    aria-label={`${code} 제거`}
                    className="text-subtle"
                  >
                    ×
                  </button>
                </span>
              </Badge>
            ))}
          </div>
          {errors.universe?.message && <span className="field__error">{errors.universe.message}</span>}
        </Card.Body>
      </Card>

      {/* 규칙 */}
      <Card>
        <Card.Header
          title="매매 규칙"
          right={
            <Button
              type="button"
              variant="outline"
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() =>
                rules.append({
                  side: 'BUY',
                  qty_mode: 'PERCENT',
                  qty_value: 10,
                  conditions: [{ indicator: 'RSI', operator: '<', value: 30 }],
                })
              }
            >
              규칙 추가
            </Button>
          }
        />
        <Card.Body className="stack gap-3">
          {rules.fields.map((field, ruleIdx) => (
            <RuleEditor
              key={field.id}
              ruleIdx={ruleIdx}
              form={form}
              onRemove={() => rules.remove(ruleIdx)}
              canRemove={rules.fields.length > 1}
            />
          ))}
          {errors.rules?.message && <span className="field__error">{errors.rules.message}</span>}
        </Card.Body>
      </Card>

      {/* 리스크 */}
      <Card>
        <Card.Header title="리스크 한도" />
        <Card.Body className="grid-cols-2">
          <Field label="최대 포지션 비중 (%)" error={errors.max_position_pct?.message}>
            <Input type="number" step="1" {...register('max_position_pct', { valueAsNumber: true })} />
          </Field>
          <Field label="일일 손실 한도 (원, 음수)" error={errors.daily_loss_limit?.message}>
            <Input type="number" step="10000" {...register('daily_loss_limit', { valueAsNumber: true })} />
          </Field>
        </Card.Body>
      </Card>

      {serverError && <ErrorCard message={serverError} />}

      <div className="row gap-2 justify-end">
        <Button type="button" variant="ghost" onClick={() => router.back()}>취소</Button>
        <Button type="submit" variant="primary" loading={isSubmitting || save.isPending}>
          {mode === 'new' ? '전략 생성' : '저장'}
        </Button>
      </div>
    </form>
  );
}

/* ============================================================
 *  하위 컴포넌트: 규칙 1건의 조건 배열 편집기
 * ============================================================ */
function RuleEditor({
  ruleIdx,
  form,
  onRemove,
  canRemove,
}: {
  ruleIdx: number;
  form: ReturnType<typeof useForm<StrategyForm>>;
  onRemove: () => void;
  canRemove: boolean;
}) {
  const { register, control, formState: { errors } } = form;
  const conditions = useFieldArray({ control, name: `rules.${ruleIdx}.conditions` });
  const ruleErr = errors.rules?.[ruleIdx];

  return (
    <div style={{ border: '1px solid var(--color-border-2)', borderRadius: 'var(--radius-md)', padding: 'var(--space-3)' }}>
      <div className="row items-center justify-between mb-3">
        <Badge variant="info">규칙 #{ruleIdx + 1}</Badge>
        {canRemove && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onRemove}
            aria-label="규칙 삭제"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>

      <div className="grid-cols-3">
        <Field label="구분">
          <Select {...register(`rules.${ruleIdx}.side`)}>
            <option value="BUY">매수</option>
            <option value="SELL">매도</option>
          </Select>
        </Field>
        <Field label="수량 방식">
          <Select {...register(`rules.${ruleIdx}.qty_mode`)}>
            <option value="FIXED">고정 수량</option>
            <option value="PERCENT">자본 대비 %</option>
            <option value="KELLY">Kelly 공식</option>
          </Select>
        </Field>
        <Field label="값" error={ruleErr?.qty_value?.message}>
          <Input type="number" step="1" {...register(`rules.${ruleIdx}.qty_value`, { valueAsNumber: true })} />
        </Field>
      </div>

      <div className="divider" />
      <div className="row items-center justify-between mb-2">
        <span className="text-strong fw-semibold text-sm">조건</span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          leftIcon={<Plus className="h-4 w-4" />}
          onClick={() => conditions.append({ indicator: 'RSI', operator: '<', value: 30 })}
        >
          조건 추가
        </Button>
      </div>

      <div className="stack gap-2">
        {conditions.fields.map((cField, cIdx) => (
          <div key={cField.id} className="row gap-2 items-end">
            <Field label="지표" className="flex-1">
              <Select {...register(`rules.${ruleIdx}.conditions.${cIdx}.indicator`)}>
                <option value="RSI">RSI</option>
                <option value="MACD">MACD</option>
                <option value="MA5">MA5</option>
                <option value="MA20">MA20</option>
                <option value="MA60">MA60</option>
                <option value="BBANDS_UPPER">볼린저 상단</option>
                <option value="BBANDS_LOWER">볼린저 하단</option>
              </Select>
            </Field>
            <Field label="연산자" className="flex-1">
              <Select {...register(`rules.${ruleIdx}.conditions.${cIdx}.operator`)}>
                <option value="<">&lt;</option>
                <option value="<=">≤</option>
                <option value="=">=</option>
                <option value=">=">≥</option>
                <option value=">">&gt;</option>
                <option value="CROSS_UP">CROSS UP</option>
                <option value="CROSS_DOWN">CROSS DOWN</option>
              </Select>
            </Field>
            <Field label="값" className="flex-1">
              <Input
                type="number"
                step="0.01"
                {...register(`rules.${ruleIdx}.conditions.${cIdx}.value`, { valueAsNumber: true })}
              />
            </Field>
            {conditions.fields.length > 1 && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => conditions.remove(cIdx)}
                aria-label="조건 삭제"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
