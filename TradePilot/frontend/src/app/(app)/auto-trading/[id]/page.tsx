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
import { StatRow } from '@/components/ui/stat-row';
import { useSaveStrategy, useStrategy } from '@/lib/api/queries/strategies';
import { usePnlReport } from '@/lib/api/queries/reports';
import { ROUTES } from '@/lib/constants';
import { formatPct, formatPnl, pnlClass } from '@/lib/utils/format';

const PnlLineChart = dynamic(() => import('@/components/charts/PnlLineChart').then((m) => m.PnlLineChart), {
  ssr: false,
  loading: () => <Skeleton height={260} />,
});

export default function StrategyDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const strategy = useStrategy(id);
  const save = useSaveStrategy();
  const perf = usePnlReport('3M');

  if (strategy.isLoading) return <Skeleton height={300} />;
  if (strategy.isError || !strategy.data || !id) {
    return (
      <ErrorCard
        message={`전략(${id})을 찾을 수 없습니다.`}
        action={<Link href={ROUTES.AUTO_TRADING}><Button variant="primary">전략 목록</Button></Link>}
      />
    );
  }
  const s = strategy.data;

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <div className="row items-center gap-3">
            <h1>{s.name}</h1>
            <Badge variant={s.status === 'ACTIVE' ? 'success' : 'default'}>
              {s.status === 'ACTIVE' ? '실행 중' : s.status}
            </Badge>
          </div>
          <p className="text-sm text-muted mt-1">{s.description}</p>
        </div>
        <div className="row gap-2">
          <Button
            variant="outline"
            onClick={() => save.mutate({ ...s, status: s.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE' })}
            loading={save.isPending}
          >
            {s.status === 'ACTIVE' ? '일시정지' : '실행'}
          </Button>
          <Link href={ROUTES.AUTO_TRADING_EDIT(s.id)}>
            <Button variant="primary">편집</Button>
          </Link>
        </div>
      </div>

      <section className="grid-cols-4 mb-4">
        <Card><Card.Body>
          <Kpi
            label="누적 손익"
            value={perf.data ? <span className={pnlClass(perf.data.summary.total_pnl)}>{formatPnl(perf.data.summary.total_pnl)}</span> : <Skeleton height={24} />}
          />
        </Card.Body></Card>
        <Card><Card.Body>
          <Kpi
            label="수익률"
            value={perf.data ? <span className={pnlClass(perf.data.summary.total_pnl_pct)}>{formatPct(perf.data.summary.total_pnl_pct)}</span> : <Skeleton height={24} />}
          />
        </Card.Body></Card>
        <Card><Card.Body>
          <Kpi label="승률" value={perf.data ? `${perf.data.summary.win_rate.toFixed(1)}%` : <Skeleton height={24} />} />
        </Card.Body></Card>
        <Card><Card.Body>
          <Kpi label="거래 횟수" value={perf.data ? `${perf.data.summary.trades}건` : <Skeleton height={24} />} />
        </Card.Body></Card>
      </section>

      <Card className="mb-4">
        <Card.Header title="자산 곡선" subtitle="최근 3개월" />
        <Card.Body>
          {perf.data && <PnlLineChart data={perf.data.series} />}
        </Card.Body>
      </Card>

      <div className="grid-cols-2">
        <Card>
          <Card.Header title="대상 종목" />
          <Card.Body className="row gap-2 flex-wrap">
            {s.universe.map((u) => (
              <Badge key={u} variant="default">{u}</Badge>
            ))}
          </Card.Body>
        </Card>
        <Card>
          <Card.Header title="규칙 요약" />
          <Card.Body className="stack gap-2">
            {s.rules.map((r, i) => (
              <StatRow
                key={i}
                label={
                  <Badge variant={r.side === 'BUY' ? 'up' : 'down'}>
                    {r.side === 'BUY' ? '매수' : '매도'} #{i + 1}
                  </Badge>
                }
                value={
                  <span className="text-sm">
                    조건 {r.conditions.length}개 · {r.qty_mode === 'PERCENT' ? `${r.qty_value}%` : r.qty_value}
                  </span>
                }
              />
            ))}
            <div className="divider" />
            <StatRow label="최대 포지션" value={`${s.risk_limit?.max_position ?? '-'}%`} />
            <StatRow label="일일 손실 한도" value={`${s.risk_limit?.daily_loss?.toLocaleString('ko-KR') ?? '-'}원`} />
          </Card.Body>
        </Card>
      </div>
    </>
  );
}
