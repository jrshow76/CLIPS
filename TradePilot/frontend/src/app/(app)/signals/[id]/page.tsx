'use client';

import { Sparkles } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Skeleton } from '@/components/ui/skeleton';
import { StatRow } from '@/components/ui/stat-row';
import { OrderModal } from '@/components/orders/OrderModal';
import { useSignals } from '@/lib/api/queries/signals';
import { ROUTES } from '@/lib/constants';
import { formatKST } from '@/lib/utils/date';
import { formatPct, pnlClass } from '@/lib/utils/format';

/**
 * 시그널 상세.
 * - useSignals 결과에서 id로 매칭 (별도 detail 엔드포인트 없을 때).
 * - "주문 실행" 버튼으로 OrderModal 띄움 → 시그널이 제안한 가격을 suggestedPrice로 전달.
 */
export default function SignalDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const signals = useSignals();
  const signal = signals.data?.find((s) => s.id === id);
  const [orderOpen, setOrderOpen] = useState(false);

  if (signals.isLoading) return <Skeleton height={400} />;
  if (signals.isError || !signal) {
    return (
      <ErrorCard
        message={`시그널(${id})을 찾을 수 없습니다.`}
        action={<Link href={ROUTES.SIGNALS}><Button variant="primary">시그널 목록으로</Button></Link>}
      />
    );
  }

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <div className="row items-center gap-3">
            <Badge variant={signal.action === 'BUY' ? 'up' : signal.action === 'SELL' ? 'down' : 'default'}>
              {signal.action === 'BUY' ? '매수' : signal.action === 'SELL' ? '매도' : '관망'}
            </Badge>
            <h1>{signal.name}</h1>
            <Badge variant="default">{signal.code}</Badge>
          </div>
          <p className="text-sm text-muted mt-1">
            {signal.strategy_name ?? signal.source} · {formatKST(signal.created_at)}
          </p>
        </div>
        <div className="row gap-2">
          <Link href={ROUTES.CHART(signal.code)}>
            <Button variant="outline">차트 보기</Button>
          </Link>
          <Button
            variant={signal.action === 'SELL' ? 'danger' : 'primary'}
            onClick={() => setOrderOpen(true)}
            disabled={signal.consumed}
          >
            {signal.consumed ? '처리 완료' : `${signal.action === 'SELL' ? '매도' : '매수'} 주문 실행`}
          </Button>
        </div>
      </div>

      <div className="grid-cols-2">
        <Card>
          <Card.Header title="시그널 정보" />
          <Card.Body className="stack gap-2">
            <StatRow label="종목" value={`${signal.name} (${signal.code})`} />
            <StatRow label="시그널 가격" value={<span className="text-num fw-semibold">{signal.price.toLocaleString('ko-KR')}원</span>} />
            <StatRow label="신뢰도" value={`${signal.confidence}%`} />
            <StatRow label="발생 시각" value={formatKST(signal.created_at)} />
            <StatRow label="상태" value={signal.consumed ? <Badge variant="success">처리 완료</Badge> : <Badge variant="info">활성</Badge>} />
          </Card.Body>
        </Card>

        <Card>
          <Card.Header
            title={<span className="row items-center gap-2"><Sparkles className="h-4 w-4 text-brand" /> 시그널 해석</span>}
          />
          <Card.Body className="stack gap-3">
            <div>
              <Badge variant="info" className="mb-2">{signal.source}</Badge>
              <p className="text-sm">
                {signal.note ?? '전략 규칙에 따라 자동 생성된 시그널입니다. 시장 상황을 고려하여 주문을 결정하세요.'}
              </p>
            </div>
            <div className="divider" />
            <StatRow
              label="제안 신뢰도"
              value={
                <div className="row items-center gap-2">
                  <div style={{ background: 'var(--color-bg-3)', width: 100, height: 6, borderRadius: 3 }}>
                    <div style={{ background: 'var(--color-brand-500)', width: `${signal.confidence}%`, height: '100%', borderRadius: 3 }} />
                  </div>
                  <span className={pnlClass(signal.confidence - 50)}>{formatPct(signal.confidence)}</span>
                </div>
              }
            />
          </Card.Body>
        </Card>
      </div>

      <OrderModal
        open={orderOpen}
        onClose={() => setOrderOpen(false)}
        code={signal.code}
        name={signal.name}
        defaultSide={signal.action === 'SELL' ? 'SELL' : 'BUY'}
        suggestedPrice={signal.price}
      />
    </>
  );
}
