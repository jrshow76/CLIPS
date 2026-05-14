'use client';

/**
 * 호가창 헤더.
 *
 * 컬럼 구성: [잔량 (좌)] [가격] [잔량 (우)]
 * - 매도호가는 상단(가격 높은 순), 매수호가는 하단(가격 높은 순)
 * - 잔량 누계 막대 그래프 정렬 기준에 맞춰 좌/우 배치
 */
export function OrderBookHeader() {
  return (
    <div
      className="grid text-xs text-subtle fw-semibold"
      style={{
        gridTemplateColumns: '1fr 96px 1fr',
        gap: 'var(--space-1)',
        padding: 'var(--space-1) var(--space-2)',
        borderBottom: '1px solid var(--color-border)',
      }}
      role="row"
    >
      <span className="text-right">매도잔량</span>
      <span className="text-center">호가</span>
      <span>매수잔량</span>
    </div>
  );
}
