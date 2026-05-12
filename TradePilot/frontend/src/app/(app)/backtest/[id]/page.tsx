'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useParams } from 'next/navigation';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Kpi } from '@/components/ui/kpi';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { useBacktestJob, useBacktestResult } from '@/lib/api/queries/backtest';
import { ROUTES } from '@/lib/constants';
import { formatPct, pnlClass } from '@/lib/utils/format';

const BacktestEquityChart = dynamic(
  () => import('@/components/charts/BacktestEquityChart').then((m) => m.BacktestEquityChart),
  { ssr: false, loading: () => <Skeleton height={360} /> },
);

export default function BacktestResultPage() {
  const params = useParams<{ id: string }>();
  const jobId = params?.id;

  const job = useBacktestJob(jobId);
  const result = useBacktestResult(job.data?.status === 'DONE' ? jobId : undefined);

  if (!jobId) return <ErrorCard message="잘못된 접근입니다." />;
  if (job.isError) return <ErrorCard message="백테스트 작업을 찾을 수 없습니다." />;

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <div className="row items-center gap-3">
            <h1>백테스트 결과</h1>
            <Badge variant="default">{jobId}</Badge>
            {job.data && (
              <Badge variant={job.data.status === 'DONE' ? 'success' : job.data.status === 'FAILED' ? 'danger' : 'info'}>
                {job.data.status}
              </Badge>
            )}
          </div>
        </div>
        <div className="row gap-2">
          <Link href={ROUTES.BACKTEST}><Button variant="outline">새 백테스트</Button></Link>
          <Link href={ROUTES.BACKTEST_HISTORY}><Button variant="ghost">과거 결과</Button></Link>
        </div>
      </div>

      {job.data && job.data.status !== 'DONE' && (
        <Card>
          <Card.Body className="stack gap-3">
            <p className="text-sm">백테스트 진행 중... ({job.data.progress.toFixed(0)}%)</p>
            <Progress value={job.data.progress} />
          </Card.Body>
        </Card>
      )}

      {result.data && (
        <>
          <section className="grid-cols-4 mt-4">
            <Card><Card.Body>
              <Kpi
                label="총 수익률"
                value={<span className={pnlClass(result.data.total_return_pct)}>{formatPct(result.data.total_return_pct)}</span>}
              />
            </Card.Body></Card>
            <Card><Card.Body><Kpi label="CAGR" value={formatPct(result.data.cagr_pct)} /></Card.Body></Card>
            <Card><Card.Body><Kpi label="최대 낙폭(MDD)" value={<span className="text-down">{formatPct(result.data.mdd_pct)}</span>} /></Card.Body></Card>
            <Card><Card.Body><Kpi label="샤프 비율" value={result.data.sharpe.toFixed(2)} /></Card.Body></Card>
          </section>

          <section className="grid-cols-4 mt-4">
            <Card><Card.Body><Kpi label="승률" value={`${result.data.win_rate.toFixed(1)}%`} /></Card.Body></Card>
            <Card><Card.Body><Kpi label="총 거래수" value={`${result.data.trades}회`} /></Card.Body></Card>
            <Card><Card.Body><Kpi label="평균 보유일" value="3.2일" /></Card.Body></Card>
            <Card><Card.Body><Kpi label="벤치마크 대비" value={<span className="text-up">+5.4%p</span>} /></Card.Body></Card>
          </section>

          <Card className="mt-4">
            <Card.Header title="자산 곡선" />
            <Card.Body>
              <BacktestEquityChart data={result.data.equity_curve} />
            </Card.Body>
          </Card>

          <Card className="mt-4">
            <Card.Header title="주요 거래" subtitle="실제 결과는 백엔드 거래 로그 연동 시 표시됩니다." />
            <Card.Body>
              <p className="text-subtle text-sm">현재 mock 모드에서는 거래 로그가 제공되지 않습니다. (BackendSenior 인계 사항)</p>
            </Card.Body>
          </Card>
        </>
      )}

      {!result.data && job.data?.status === 'DONE' && <Skeleton height={400} className="mt-4" />}
    </>
  );
}
