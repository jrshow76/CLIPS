'use client';

import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { ROUTES } from '@/lib/constants';

import { StrategyForm } from '../_components/StrategyForm';

export default function NewStrategyPage() {
  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>새 전략</h1>
          <p>시뮬레이션 모드로 안전하게 검증 후 LIVE 모드로 전환하세요.</p>
        </div>
        <Link href={ROUTES.AUTO_TRADING}>
          <Button variant="outline">← 목록으로</Button>
        </Link>
      </div>
      <StrategyForm mode="new" />
    </>
  );
}
