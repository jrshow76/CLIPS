'use client';

import { useState } from 'react';

import { BacktestEquityChart } from '@/components/charts/BacktestEquityChart';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Field, Input } from '@/components/ui/input';
import { Kpi } from '@/components/ui/kpi';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useBacktestResult, useStartBacktest } from '@/lib/api/queries/backtest';
import { useStrategies } from '@/lib/api/queries/strategies';
import { formatPct, pnlClass } from '@/lib/utils/format';

/**
 * 백테스트 페이지.
 * FrontendDev 가이드: 결과 상세는 /backtest/[jobId]에 별도 페이지로 분리 가능.
 */
export default function BacktestPage() {
  const strategies = useStrategies();
  const start = useStartBacktest();
  const [strategyId, setStrategyId] = useState('');
  const [from, setFrom] = useState('2025-01-01');
  const [to, setTo] = useState('2026-05-12');
  const [initialCash, setInitialCash] = useState(10_000_000);
  const [jobId, setJobId] = useState<string | null>(null);
  const result = useBacktestResult(jobId ?? undefined);

  async function onRun(e: React.FormEvent) {
    e.preventDefault();
    if (!strategyId) return;
    const job = await start.mutateAsync({
      strategy_id: strategyId,
      universe: [],
      from,
      to,
      initial_cash: initialCash,
    });
    setJobId(job.job_id);
  }

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>백테스트</h1>
          <p>과거 데이터로 전략을 검증합니다.</p>
        </div>
      </div>

      <Card>
        <Card.Header title="실행 설정" />
        <Card.Body>
          <form onSubmit={onRun} className="form-grid">
            <Field label="전략" required>
              <Select value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
                <option value="">전략 선택</option>
                {strategies.data?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="초기 자본 (원)">
              <Input
                type="number"
                value={initialCash}
                onChange={(e) => setInitialCash(Number(e.target.value))}
              />
            </Field>
            <Field label="시작일">
              <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
            </Field>
            <Field label="종료일">
              <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
            </Field>
            <div className="field--full row justify-end">
              <Button type="submit" variant="primary" loading={start.isPending}>
                백테스트 실행
              </Button>
            </div>
          </form>
        </Card.Body>
      </Card>

      {jobId && (
        <>
          <div className="grid-cols-4 mt-6">
            <Card><Card.Body>
              <Kpi
                label="총 수익률"
                value={
                  result.data ? (
                    <span className={pnlClass(result.data.total_return_pct)}>{formatPct(result.data.total_return_pct)}</span>
                  ) : (
                    <Skeleton height={24} />
                  )
                }
              />
            </Card.Body></Card>
            <Card><Card.Body><Kpi label="CAGR" value={result.data ? formatPct(result.data.cagr_pct) : <Skeleton height={24} />} /></Card.Body></Card>
            <Card><Card.Body><Kpi label="최대 낙폭(MDD)" value={result.data ? formatPct(result.data.mdd_pct) : <Skeleton height={24} />} /></Card.Body></Card>
            <Card><Card.Body><Kpi label="샤프 비율" value={result.data ? result.data.sharpe.toFixed(2) : <Skeleton height={24} />} /></Card.Body></Card>
          </div>

          <Card className="mt-4">
            <Card.Header title="자산 곡선" />
            <Card.Body>
              {result.data ? <BacktestEquityChart data={result.data.equity_curve} /> : <Skeleton height={360} />}
            </Card.Body>
          </Card>
        </>
      )}
    </>
  );
}
