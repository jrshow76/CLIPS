'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { ErrorCard } from '@/components/ui/error-card';
import { Skeleton } from '@/components/ui/skeleton';
import { useStrategy } from '@/lib/api/queries/strategies';
import { ROUTES } from '@/lib/constants';

import { StrategyForm } from '../../_components/StrategyForm';

export default function StrategyEditPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const strategy = useStrategy(id);

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>전략 편집</h1>
          {strategy.data && <p className="text-sm text-muted">{strategy.data.name}</p>}
        </div>
        {id && (
          <Link href={ROUTES.AUTO_TRADING_DETAIL(id)}>
            <Button variant="outline">← 상세로</Button>
          </Link>
        )}
      </div>

      {strategy.isLoading && <Skeleton height={400} />}
      {strategy.isError && <ErrorCard message="전략을 불러올 수 없습니다." />}
      {strategy.data && <StrategyForm mode="edit" initial={strategy.data} />}
    </>
  );
}
