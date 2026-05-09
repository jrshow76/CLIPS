'use client'

/**
 * OrderList - 주문 내역 목록 + 환불 요청 버튼
 * 마이페이지 > 주문 내역 탭에서 사용
 */

import { useState } from 'react'
import { Button } from '@/components/common/Button'
import { useToast } from '@/components/common/Toast'
import { useOrders, useRequestRefund } from '@/hooks/useOrders'
import type { OrderStatus, OrderSummary } from '@/lib/api/orders'

const STATUS_LABEL: Record<OrderStatus, string> = {
  PENDING: '결제 대기',
  PAID: '결제 완료',
  CANCELLED: '취소됨',
  REFUND_REQUESTED: '환불 요청 중',
  REFUNDED: '환불 완료',
}

const STATUS_BADGE_CLASS: Record<OrderStatus, string> = {
  PENDING: 'badge--warning',
  PAID: 'badge--success',
  CANCELLED: 'badge--neutral',
  REFUND_REQUESTED: 'badge--warning',
  REFUNDED: 'badge--neutral',
}

function formatPrice(price: number): string {
  return price.toLocaleString('ko-KR') + '원'
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

/* --------------------------------------------------------------------------
   환불 요청 모달
   -------------------------------------------------------------------------- */
function RefundModal({
  orderId,
  onClose,
}: {
  orderId: number
  onClose: () => void
}) {
  const toast = useToast()
  const [reason, setReason] = useState('')
  const requestRefund = useRequestRefund(orderId)

  const handleConfirm = async () => {
    if (!reason.trim()) {
      toast.warning('환불 사유를 입력해주세요.')
      return
    }
    try {
      await requestRefund.mutateAsync({ reason })
      toast.success('환불 요청이 접수되었습니다.')
      onClose()
    } catch (e: any) {
      toast.error(e?.message ?? '환불 요청에 실패했습니다.')
    }
  }

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="refund-modal-title"
    >
      <div className="modal">
        <div className="modal__header">
          <h2 className="modal__title" id="refund-modal-title">
            환불 요청
          </h2>
          <button
            className="btn btn--ghost btn--icon"
            aria-label="모달 닫기"
            onClick={onClose}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="modal__body">
          <p style={{ marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
            환불 요청 후 운영팀이 검토하여 처리합니다. 일반적으로 영업일 기준
            3~5일 이내에 처리됩니다.
          </p>
          <div className="form-field">
            <label className="form-label form-label--required" htmlFor="refund-reason">
              환불 사유
            </label>
            <textarea
              id="refund-reason"
              className="form-textarea"
              rows={4}
              placeholder="환불을 요청하는 사유를 상세히 입력해주세요."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={500}
            />
          </div>
        </div>
        <div className="modal__footer">
          <Button variant="ghost" onClick={onClose}>
            취소
          </Button>
          <Button
            variant="danger"
            onClick={handleConfirm}
            loading={requestRefund.isPending}
          >
            환불 요청
          </Button>
        </div>
      </div>
    </div>
  )
}

/* --------------------------------------------------------------------------
   주문 카드
   -------------------------------------------------------------------------- */
function OrderCard({ order }: { order: OrderSummary }) {
  const [showRefundModal, setShowRefundModal] = useState(false)
  const canRefund = order.status === 'PAID'

  return (
    <>
      <article
        className="order-card"
        style={{
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-5)',
          display: 'flex',
          gap: 'var(--space-4)',
          alignItems: 'flex-start',
        }}
        aria-label={`주문: ${order.item.title}`}
      >
        {/* 썸네일 */}
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: 'var(--radius-lg)',
            backgroundColor: 'var(--color-bg-muted)',
            flexShrink: 0,
            overflow: 'hidden',
          }}
          aria-hidden="true"
        >
          {order.item.thumbnailUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={order.item.thumbnailUrl}
              alt={order.item.title}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <div
              style={{
                width: '100%',
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.25rem',
              }}
            >
              🖼
            </div>
          )}
        </div>

        {/* 정보 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              marginBottom: 'var(--space-2)',
            }}
          >
            <span
              className={`badge ${STATUS_BADGE_CLASS[order.status]}`}
              aria-label={`주문 상태: ${STATUS_LABEL[order.status]}`}
            >
              {STATUS_LABEL[order.status]}
            </span>
          </div>
          <h3
            className="truncate"
            style={{
              fontSize: 'var(--font-size-sm)',
              fontWeight: 'var(--font-weight-semibold)',
              color: 'var(--color-text-primary)',
              marginBottom: 'var(--space-1)',
            }}
          >
            {order.item.title}
          </h3>
          <p
            style={{
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-text-tertiary)',
              marginBottom: 'var(--space-3)',
            }}
          >
            주문일: {formatDate(order.createdAt)}
            {order.paidAt && ` · 결제일: ${formatDate(order.paidAt)}`}
          </p>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span
              style={{
                fontSize: 'var(--font-size-base)',
                fontWeight: 'var(--font-weight-bold)',
                color: 'var(--color-text-primary)',
              }}
            >
              {formatPrice(order.paidAmount)}
            </span>
            {canRefund && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowRefundModal(true)}
              >
                환불 요청
              </Button>
            )}
          </div>
        </div>
      </article>

      {showRefundModal && (
        <RefundModal
          orderId={order.orderId}
          onClose={() => setShowRefundModal(false)}
        />
      )}
    </>
  )
}

/* --------------------------------------------------------------------------
   메인 컴포넌트
   -------------------------------------------------------------------------- */
export function OrderList() {
  const [page, setPage] = useState(0)
  const { data, isLoading, isError } = useOrders({ page, size: 10 })

  if (isLoading) {
    return (
      <div
        style={{
          padding: 'var(--space-12)',
          textAlign: 'center',
          color: 'var(--color-text-tertiary)',
        }}
      >
        주문 내역을 불러오는 중...
      </div>
    )
  }

  if (isError) {
    return (
      <div
        style={{
          padding: 'var(--space-12)',
          textAlign: 'center',
          color: 'var(--color-error)',
        }}
      >
        주문 내역을 불러올 수 없습니다.
      </div>
    )
  }

  if (!data || data.content.length === 0) {
    return (
      <div
        style={{
          padding: 'var(--space-20)',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            fontSize: '2.5rem',
            marginBottom: 'var(--space-4)',
          }}
          aria-hidden="true"
        >
          🛒
        </div>
        <p
          style={{
            fontSize: 'var(--font-size-lg)',
            fontWeight: 'var(--font-weight-bold)',
            color: 'var(--color-text-secondary)',
            marginBottom: 'var(--space-2)',
          }}
        >
          구매 내역이 없습니다
        </p>
        <p
          style={{
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-tertiary)',
          }}
        >
          마음에 드는 상품을 찾아 구매해보세요.
        </p>
      </div>
    )
  }

  return (
    <div>
      <div
        style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}
        role="list"
        aria-label="주문 목록"
      >
        {data.content.map((order) => (
          <div key={order.orderId} role="listitem">
            <OrderCard order={order} />
          </div>
        ))}
      </div>

      {/* 페이지네이션 */}
      {data.totalPages > 1 && (
        <nav
          className="pagination"
          style={{ marginTop: 'var(--space-8)' }}
          aria-label="주문 내역 페이지 이동"
        >
          <button
            className={`pagination__item ${page === 0 ? 'pagination__item--disabled' : ''}`}
            aria-label="이전 페이지"
            aria-disabled={page === 0}
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          {Array.from({ length: data.totalPages }, (_, i) => (
            <button
              key={i}
              className={`pagination__item ${i === page ? 'pagination__item--active' : ''}`}
              aria-label={`${i + 1} 페이지`}
              aria-current={i === page ? 'page' : undefined}
              onClick={() => setPage(i)}
            >
              {i + 1}
            </button>
          ))}
          <button
            className={`pagination__item ${page >= data.totalPages - 1 ? 'pagination__item--disabled' : ''}`}
            aria-label="다음 페이지"
            aria-disabled={page >= data.totalPages - 1}
            disabled={page >= data.totalPages - 1}
            onClick={() => setPage((p) => Math.min(data.totalPages - 1, p + 1))}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        </nav>
      )}
    </div>
  )
}
