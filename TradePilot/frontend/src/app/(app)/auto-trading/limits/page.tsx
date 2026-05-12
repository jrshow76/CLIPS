'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';

import { Banner } from '@/components/ui/banner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Field, Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { StatRow } from '@/components/ui/stat-row';
import { useTradingLimits, useUpdateTradingLimits } from '@/lib/api/queries/trading-limits';
import { ROUTES } from '@/lib/constants';
import { tradingLimitsSchema, type TradingLimitsForm } from '@/lib/forms/zod-schemas';
import { zodResolver } from '@/lib/forms/zod-resolver';
import { formatCurrency } from '@/lib/utils/format';

export default function TradingLimitsPage() {
  const limits = useTradingLimits();
  const update = useUpdateTradingLimits();

  const form = useForm<TradingLimitsForm>({
    resolver: zodResolver<TradingLimitsForm>(tradingLimitsSchema),
    defaultValues: { daily_buy_limit: 0, daily_loss_limit: 0, max_position_pct: 0, per_order_limit: 0 },
  });
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = form;

  useEffect(() => {
    if (limits.data) {
      reset({
        daily_buy_limit: limits.data.daily_buy_limit,
        daily_loss_limit: limits.data.daily_loss_limit,
        max_position_pct: limits.data.max_position_pct,
        per_order_limit: limits.data.per_order_limit,
      });
    }
  }, [limits.data, reset]);

  const onSubmit = handleSubmit(async (values) => {
    await update.mutateAsync(values);
  });

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>매매 한도</h1>
          <p>일일 매수/손실 한도와 개별 주문 한도를 설정합니다.</p>
        </div>
        <Link href={ROUTES.AUTO_TRADING}><Button variant="outline">← 자동매매</Button></Link>
      </div>

      {limits.isLoading && <Skeleton height={300} />}
      {limits.isError && <ErrorCard message="한도 정보를 불러올 수 없습니다." />}

      {limits.data && (
        <div className="grid-cols-2">
          <Card>
            <Card.Header title="오늘 사용 현황" />
            <Card.Body className="stack gap-4">
              <Banner variant={limits.data.buy_progress >= 80 ? 'warning' : 'info'}>
                일일 매수 한도의 <strong>{limits.data.buy_progress.toFixed(1)}%</strong>를 사용했습니다.
              </Banner>
              <div>
                <StatRow
                  label="매수 사용액"
                  value={`${formatCurrency(limits.data.used_buy_today)} / ${formatCurrency(limits.data.daily_buy_limit)}`}
                />
                <Progress value={limits.data.buy_progress} />
              </div>
              <div>
                <StatRow
                  label="손실 누적"
                  value={`${formatCurrency(limits.data.used_loss_today)} / ${formatCurrency(limits.data.daily_loss_limit)}`}
                />
                <Progress value={limits.data.loss_progress} variant={limits.data.loss_progress >= 80 ? 'danger' : 'default'} />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Header title="한도 설정" />
            <form onSubmit={onSubmit} noValidate>
              <Card.Body className="stack gap-4">
                <Field label="일일 매수 한도 (원)" required error={errors.daily_buy_limit?.message}>
                  <Input type="number" step="100000" {...register('daily_buy_limit', { valueAsNumber: true })} />
                </Field>
                <Field
                  label="일일 손실 한도 (원, 음수)"
                  required
                  error={errors.daily_loss_limit?.message}
                  hint="이 금액에 도달하면 자동매매가 즉시 중단됩니다."
                >
                  <Input type="number" step="10000" {...register('daily_loss_limit', { valueAsNumber: true })} />
                </Field>
                <Field label="개별 주문 한도 (원)" required error={errors.per_order_limit?.message}>
                  <Input type="number" step="100000" {...register('per_order_limit', { valueAsNumber: true })} />
                </Field>
                <Field label="최대 포지션 비중 (%)" required error={errors.max_position_pct?.message}>
                  <Input type="number" step="1" min="0" max="100" {...register('max_position_pct', { valueAsNumber: true })} />
                </Field>
              </Card.Body>
              <Card.Footer>
                <div className="row gap-2 justify-end">
                  <Button type="submit" variant="primary" loading={isSubmitting || update.isPending}>저장</Button>
                </div>
              </Card.Footer>
            </form>
          </Card>
        </div>
      )}
    </>
  );
}
