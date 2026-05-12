'use client';

import { Pause, Play, Plus } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { useStrategies } from '@/lib/api/queries/strategies';
import { useTradeModeStore } from '@/stores/trade-mode-store';

export default function AutoTradingPage() {
  const strategies = useStrategies();
  const mode = useTradeModeStore((s) => s.mode);

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>자동매매</h1>
          <p>전략 기반 자동매매를 관리합니다. 현재 모드: <Badge variant={mode === 'LIVE' ? 'live' : 'sim'} dot>{mode}</Badge></p>
        </div>
        <Button variant="primary" leftIcon={<Plus className="h-4 w-4" />}>
          새 전략
        </Button>
      </div>

      {strategies.isLoading && <Skeleton height={160} />}
      {strategies.isError && <ErrorCard message="전략 목록을 불러올 수 없습니다." />}

      {strategies.data && strategies.data.length === 0 && (
        <EmptyState
          title="등록된 전략이 없습니다."
          description="시뮬레이션 모드로 안전하게 첫 전략을 만들어보세요."
          action={<Button variant="primary">전략 만들기</Button>}
        />
      )}

      <div className="grid-cols-2">
        {strategies.data?.map((s) => (
          <Card key={s.id}>
            <Card.Header
              title={s.name}
              subtitle={s.description}
              right={
                <Badge variant={s.status === 'ACTIVE' ? 'success' : 'default'}>
                  {s.status === 'ACTIVE' ? '실행 중' : s.status}
                </Badge>
              }
            />
            <Card.Body>
              <div className="row gap-2 flex-wrap">
                <span className="text-subtle text-xs">유니버스</span>
                {s.universe.map((u) => (
                  <Badge key={u} variant="default">
                    {u}
                  </Badge>
                ))}
              </div>
              <div className="divider" />
              <p className="text-sm text-muted">
                규칙 {s.rules.length}개 · 최대 포지션 {s.risk_limit?.max_position ?? '-'}% · 일일 손실 한도{' '}
                {s.risk_limit?.daily_loss?.toLocaleString('ko-KR') ?? '-'}원
              </p>
            </Card.Body>
            <Card.Footer>
              <div className="row gap-2 justify-end">
                {s.status === 'ACTIVE' ? (
                  <Button variant="outline" leftIcon={<Pause className="h-4 w-4" />}>
                    일시정지
                  </Button>
                ) : (
                  <Button variant="primary" leftIcon={<Play className="h-4 w-4" />}>
                    실행
                  </Button>
                )}
                <Button variant="ghost">상세</Button>
              </div>
            </Card.Footer>
          </Card>
        ))}
      </div>
    </>
  );
}
