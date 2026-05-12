'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';

import { Banner } from '@/components/ui/banner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Field, Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useStartBacktest } from '@/lib/api/queries/backtest';
import { useStrategies } from '@/lib/api/queries/strategies';
import { ROUTES } from '@/lib/constants';
import { backtestFormSchema, type BacktestForm } from '@/lib/forms/zod-schemas';
import { applyFieldErrors, toUserMessage } from '@/lib/forms/extract-field-errors';
import { zodResolver } from '@/lib/forms/zod-resolver';
import { useState } from 'react';

export default function BacktestPage() {
  const router = useRouter();
  const strategies = useStrategies();
  const start = useStartBacktest();
  const [serverError, setServerError] = useState<string | null>(null);

  const form = useForm<BacktestForm>({
    resolver: zodResolver<BacktestForm>(backtestFormSchema),
    defaultValues: {
      strategy_id: '',
      from: '2025-01-01',
      to: '2026-05-12',
      initial_cash: 10_000_000,
      slippage_bps: 5,
      fee_bps: 15,
    },
  });
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = form;

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      const job = await start.mutateAsync({
        strategy_id: values.strategy_id,
        universe: [],
        from: values.from,
        to: values.to,
        initial_cash: values.initial_cash,
        slippage_bps: values.slippage_bps,
        fee_bps: values.fee_bps,
      });
      router.push(ROUTES.BACKTEST_DETAIL(job.job_id));
    } catch (err) {
      if (!applyFieldErrors<BacktestForm>(err, setError)) {
        setServerError(toUserMessage(err));
      }
    }
  });

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>백테스트</h1>
          <p>과거 데이터로 전략을 검증합니다.</p>
        </div>
        <Link href={ROUTES.BACKTEST_HISTORY}>
          <Button variant="outline">과거 결과 →</Button>
        </Link>
      </div>

      {strategies.data && strategies.data.length === 0 && (
        <Banner variant="warning">
          등록된 전략이 없습니다.{' '}
          <Link href={ROUTES.AUTO_TRADING_NEW} className="underline">새 전략 만들기</Link>
        </Banner>
      )}

      <Card>
        <Card.Header title="실행 설정" />
        <form onSubmit={onSubmit} noValidate>
          <Card.Body>
            <div className="form-grid grid-cols-2">
              <Field label="전략" required error={errors.strategy_id?.message}>
                <Select {...register('strategy_id')}>
                  <option value="">전략 선택</option>
                  {strategies.data?.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </Select>
              </Field>
              <Field label="초기 자본 (원)" required error={errors.initial_cash?.message}>
                <Input type="number" step="100000" {...register('initial_cash', { valueAsNumber: true })} />
              </Field>
              <Field label="시작일" required error={errors.from?.message}>
                <Input type="date" {...register('from')} />
              </Field>
              <Field label="종료일" required error={errors.to?.message}>
                <Input type="date" {...register('to')} />
              </Field>
              <Field label="슬리피지 (bps)" hint="1bp = 0.01%" error={errors.slippage_bps?.message}>
                <Input type="number" step="1" {...register('slippage_bps', { valueAsNumber: true })} />
              </Field>
              <Field label="수수료 (bps)" error={errors.fee_bps?.message}>
                <Input type="number" step="1" {...register('fee_bps', { valueAsNumber: true })} />
              </Field>
            </div>
            {serverError && <ErrorCard className="mt-3" message={serverError} />}
          </Card.Body>
          <Card.Footer>
            <div className="row gap-2 justify-end">
              <Button type="submit" variant="primary" loading={isSubmitting || start.isPending}>
                백테스트 실행
              </Button>
            </div>
          </Card.Footer>
        </form>
      </Card>

      {strategies.isLoading && <Skeleton height={300} className="mt-4" />}
    </>
  );
}
