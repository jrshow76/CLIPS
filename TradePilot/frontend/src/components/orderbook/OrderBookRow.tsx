'use client';

import { cn } from '@/lib/utils/cn';

/** 한 호가 row 매개변수. */
export interface OrderBookRowProps {
  /** 'ask'(매도) 또는 'bid'(매수) - 색상/막대 정렬에 영향 */
  side: 'ask' | 'bid';
  /** 가격 (원) */
  price: number;
  /** 잔량 (주) */
  qty: number;
  /** 누적 잔량 대비 비율 (0~1) - 막대 그래프 폭 결정 */
  ratio: number;
  /** 최우선 호가 여부 (1단계) - 강조 표시 */
  isBest?: boolean;
  /** 행 클릭 시 콜백 (가격 전달) - 주문 모달 자동 가격 입력에 사용 */
  onClickPrice?: (price: number) => void;
}

/**
 * 호가창의 한 행 (호가 1단계).
 *
 * 색상 컨벤션 (한국 주식시장 표준):
 * - 매도(ask) = 파랑 ``.text-down``
 * - 매수(bid) = 빨강 ``.text-up``
 *
 * 배경 막대 (누적 잔량 시각화):
 * - 잔량 비율만큼 트랙 색상이 채워짐 (매수=오른쪽→왼쪽, 매도=왼쪽→오른쪽)
 *
 * 클릭 시 ``onClickPrice(price)`` 호출 - 차트 페이지에서 주문 모달 자동 가격 입력.
 */
export function OrderBookRow({
  side,
  price,
  qty,
  ratio,
  isBest = false,
  onClickPrice,
}: OrderBookRowProps) {
  const isAsk = side === 'ask';
  const priceColor = isAsk ? 'text-down' : 'text-up';
  const barColor = isAsk ? 'rgba(59, 130, 246, 0.18)' : 'rgba(239, 68, 68, 0.18)';
  // 매도는 좌측 잔량 슬롯에, 매수는 우측 잔량 슬롯에 표시
  const widthPct = Math.min(100, Math.max(0, ratio * 100));

  const handleClick = () => {
    if (price > 0) onClickPrice?.(price);
  };

  return (
    <div
      role="row"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      className={cn(
        'grid items-center text-num cursor-pointer transition-colors',
        isBest && 'fw-semibold',
      )}
      style={{
        gridTemplateColumns: '1fr 96px 1fr',
        gap: 'var(--space-1)',
        padding: 'var(--space-1) var(--space-2)',
        fontSize: 12,
        minHeight: 28,
      }}
      aria-label={`${isAsk ? '매도' : '매수'} ${price.toLocaleString('ko-KR')}원, 잔량 ${qty.toLocaleString('ko-KR')}주${isBest ? ', 최우선 호가' : ''}`}
    >
      {/* 매도 잔량 - 좌측 슬롯, 막대는 우측 정렬 */}
      <div
        className="relative text-right"
        style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}
      >
        {isAsk && (
          <span
            aria-hidden
            className="absolute inset-y-0 right-0"
            style={{ width: `${widthPct}%`, background: barColor, borderRadius: 2 }}
          />
        )}
        <span className="relative">
          {isAsk ? qty.toLocaleString('ko-KR') : ''}
        </span>
      </div>

      {/* 가격 */}
      <div
        className={cn('text-center', priceColor)}
        style={{ fontVariantNumeric: 'tabular-nums' }}
      >
        {price.toLocaleString('ko-KR')}
      </div>

      {/* 매수 잔량 - 우측 슬롯, 막대는 좌측 정렬 */}
      <div
        className="relative"
        style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'flex-start' }}
      >
        {!isAsk && (
          <span
            aria-hidden
            className="absolute inset-y-0 left-0"
            style={{ width: `${widthPct}%`, background: barColor, borderRadius: 2 }}
          />
        )}
        <span className="relative">
          {!isAsk ? qty.toLocaleString('ko-KR') : ''}
        </span>
      </div>
    </div>
  );
}
