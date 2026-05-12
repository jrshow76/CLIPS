'use client';

import { LayoutList, Pause, Play, Plus, Settings as SettingsIcon, Sliders } from 'lucide-react';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { useSaveStrategy, useStrategies } from '@/lib/api/queries/strategies';
import { ROUTES } from '@/lib/constants';
import { useTradeModeStore } from '@/stores/trade-mode-store';
import type { Strategy } from '@/types/strategy';

export default function AutoTradingPage() {
  const strategies = useStrategies();
  const save = useSaveStrategy();
  const mode = useTradeModeStore((s) => s.mode);

  function toggleActive(s: Strategy) {
    save.mutate({ ...s, status: s.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE' });
  }

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>자동매매</h1>
          <p>
            전략 기반 자동매매를 관리합니다. 현재 모드:{' '}
            <Badge variant={mode === 'LIVE' ? 'live' : 'sim'} dot>{mode}</Badge>
          </p>
        </div>
        <div className="row gap-2">
          <Link href={ROUTES.AUTO_TRADING_LIMITS}><Button variant="outline" leftIcon={<Sliders className="h-4 w-4" />}>한도 설정</Button></Link>
          <Link href={ROUTES.AUTO_TRADING_ORDERS}><Button variant="outline" leftIcon={<LayoutList className="h-4 w-4" />}>주문 내역</Button></Link>
          <Link href={ROUTES.AUTO_TRADING_NEW}>
            <Button variant="primary" leftIcon={<Plus className="h-4 w-4" />}>새 전략</Button>
          </Link>
        </div>
      </div>

      {strategies.isLoading && <Skeleton height={160} />}
      {strategies.isError && <ErrorCard message="전략 목록을 불러올 수 없습니다." />}

      {strategies.data && strategies.data.length === 0 && (
        <EmptyState
          title="등록된 전략이 없습니다."
          description="시뮬레이션 모드로 안전하게 첫 전략을 만들어보세요."
          action={
            <Link href={ROUTES.AUTO_TRADING_NEW}>
              <Button variant="primary">전략 만들기</Button>
            </Link>
          }
        />
      )}

      <div className="grid-cols-2">
        {strategies.data?.map((s) => (
          <Card key={s.id}>
            <Card.Header
              title={
                <Link href={ROUTES.AUTO_TRADING_DETAIL(s.id)} className="hover:underline">
                  {s.name}
                </Link>
              }
              subtitle={s.description}
              right={
                <div className="row items-center gap-2">
                  <Badge variant={s.status === 'ACTIVE' ? 'success' : 'default'}>
                    {s.status === 'ACTIVE' ? '실행 중' : s.status}
                  </Badge>
                  <Switch
                    checked={s.status === 'ACTIVE'}
                    onChange={() => toggleActive(s)}
                    ariaLabel="활성 토글"
                  />
                </div>
              }
            />
            <Card.Body>
              <div className="row gap-2 flex-wrap">
                <span className="text-subtle text-xs">유니버스</span>
                {s.universe.map((u) => (
                  <Badge key={u} variant="default">{u}</Badge>
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
                <Button
                  variant="outline"
                  leftIcon={s.status === 'ACTIVE' ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  onClick={() => toggleActive(s)}
                >
                  {s.status === 'ACTIVE' ? '일시정지' : '실행'}
                </Button>
                <Link href={ROUTES.AUTO_TRADING_EDIT(s.id)}>
                  <Button variant="ghost" leftIcon={<SettingsIcon className="h-4 w-4" />}>편집</Button>
                </Link>
                <Link href={ROUTES.AUTO_TRADING_DETAIL(s.id)}>
                  <Button variant="primary">상세</Button>
                </Link>
              </div>
            </Card.Footer>
          </Card>
        ))}
      </div>
    </>
  );
}
