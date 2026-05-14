'use client';

import { useMemo } from 'react';

import { OrderBookHeader } from './OrderBookHeader';
import { OrderBookRow } from './OrderBookRow';

import { Badge } from '@/components/ui/badge';
import { useRealtimeOrderbook } from '@/hooks/useRealtimeOrderbook';

export interface OrderBookProps {
  /** 종목 코드 (6자리). 빈 값이면 빈 컴포넌트 렌더. */
  stockCode: string | undefined | null;
  /** 호가 가격 클릭 시 콜백. 주문 모달 가격 자동 입력에 사용. */
  onPriceClick?: (price: number) => void;
}

/**
 * 호가창 (Level 2) - 매수/매도 10단계.
 *
 * 표시 규칙:
 * - 매도 10 → 매도 1 (상단, 가격 내림차순)
 * - 매수 1 → 매수 10 (하단, 가격 내림차순)
 * - 매수 = 빨강(상승색), 매도 = 파랑(하락색) - 한국 시장 표준
 * - 누적 잔량 막대 그래프 배경 (각 단계의 잔량을 최대 잔량 대비 비율로 표시)
 * - 최우선 호가(1단계)는 굵게 강조
 * - 가격 클릭 시 ``onPriceClick(price)`` 호출 → 주문 모달에 가격 prefill
 *
 * 실시간 연결: ``useRealtimeOrderbook`` hook이 ``/ws/orderbook`` 구독.
 */
export function OrderBook({ stockCode, onPriceClick }: OrderBookProps) {
  const ob = useRealtimeOrderbook(stockCode);

  // 누적 잔량 막대 그래프 폭 계산 기준 = 매수/매도 전체 최대 잔량
  const maxQty = useMemo(() => {
    let m = 0;
    for (const l of ob.bids) if (l.qty > m) m = l.qty;
    for (const l of ob.asks) if (l.qty > m) m = l.qty;
    return m;
  }, [ob.bids, ob.asks]);

  // 매도는 가격 내림차순(상단에 매도10이 가장 멀고 매도1이 가장 가까운 표시)
  const asksDisplay = useMemo(() => [...ob.asks].reverse(), [ob.asks]);

  if (!stockCode) {
    return (
      <div
        className="text-subtle text-sm text-center"
        style={{ padding: 'var(--space-4)' }}
      >
        종목을 선택하세요.
      </div>
    );
  }

  if (ob.bids.length === 0 && ob.asks.length === 0) {
    return (
      <div
        className="text-subtle text-sm text-center"
        style={{ padding: 'var(--space-4)' }}
        role="status"
      >
        호가 데이터를 불러오는 중...
      </div>
    );
  }

  return (
    <div className="orderbook" role="table" aria-label="호가창">
      <div
        className="row items-center justify-between"
        style={{ padding: 'var(--space-1) var(--space-2)' }}
      >
        <span className="text-xs text-subtle">10단계 호가</span>
        {ob.isLive && (
          <Badge variant="success" dot>
            LIVE
          </Badge>
        )}
      </div>
      <OrderBookHeader />
      {/* 매도호가: 10 → 1 (가격 내림차순) */}
      <div role="rowgroup" data-side="ask">
        {asksDisplay.map((level, idx) => {
          // asksDisplay의 마지막 (index 9) = 매도 1단계
          const originalIdx = ob.asks.length - 1 - idx;
          const isBest = originalIdx === 0;
          return (
            <OrderBookRow
              key={`ask-${originalIdx}-${level.price}`}
              side="ask"
              price={level.price}
              qty={level.qty}
              ratio={maxQty > 0 ? level.qty / maxQty : 0}
              isBest={isBest}
              onClickPrice={onPriceClick}
            />
          );
        })}
      </div>

      {/* 매수/매도 1단계 사이 구분선 */}
      <div
        className="divider"
        style={{ margin: 0, borderColor: 'var(--color-border)' }}
      />

      {/* 매수호가: 1 → 10 (가격 내림차순) */}
      <div role="rowgroup" data-side="bid">
        {ob.bids.map((level, idx) => (
          <OrderBookRow
            key={`bid-${idx}-${level.price}`}
            side="bid"
            price={level.price}
            qty={level.qty}
            ratio={maxQty > 0 ? level.qty / maxQty : 0}
            isBest={idx === 0}
            onClickPrice={onPriceClick}
          />
        ))}
      </div>

      {/* 합산 잔량 */}
      <div
        className="row items-center justify-between text-xs"
        style={{
          padding: 'var(--space-1) var(--space-2)',
          borderTop: '1px solid var(--color-border)',
        }}
      >
        <span className="text-down">
          매도 합계 <span className="text-num">{ob.totalAskQty.toLocaleString('ko-KR')}</span>
        </span>
        <span className="text-up">
          매수 합계 <span className="text-num">{ob.totalBidQty.toLocaleString('ko-KR')}</span>
        </span>
      </div>
    </div>
  );
}
