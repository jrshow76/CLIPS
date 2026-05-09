'use client'

/**
 * SubscriptionList - 구독 내역 목록 + 해지 요청 버튼
 * 마이페이지 > 구독 내역 탭에서 사용
 */

import { useState } from 'react'
import { Button } from '@/components/common/Button'
import { useToast } from '@/components/common/Toast'
import { useSubscriptions, useCancelSubscription, useReactivateSubscription } from '@/hooks/useSubscriptions'
import type { SubscriptionStatus, SubscriptionSummary } from '@/types/subscription'

const STATUS_LABEL: Record<SubscriptionStatus, string> = {
  ACTIVE: '구독 중',
  CANCEL_REQUESTED: '해지 예정',
  CANCELLED: '해지됨',
}

const STATUS_BADGE_CLASS: Record<SubscriptionStatus, string> = {
  ACTIVE: 'badge--success',
  CANCEL_REQUESTED: 'badge--warning',
  CANCELLED: 'badge--neutral',
}

function formatPrice(price: number): string {
  return price.toLocaleString('ko-KR') + '원'
}

function formatDate(dateString?: string): string {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

/* --------------------------------------------------------------------------
   해지 확인 모달
   -------------------------------------------------------------------------- */
function CancelConfirmModal({
  subscription,
  onConfirm,
  onClose,
  isLoading,
}: {
  subscription: SubscriptionSummary
  onConfirm: () => void
  onClose: () => void
  isLoading: boolean
}) {
  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cancel-modal-title"
    >
      <div className="modal">
        <div className="modal__header">
          <h2 className="modal__title" id="cancel-modal-title">
            구독 해지
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
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-secondary)',
              lineHeight: 'var(--line-height-relaxed)',
              marginBottom: 'var(--space-4)',
            }}
          >
            <strong>{subscription.itemTitle}</strong> 상품의{' '}
            <strong>{subscription.planName}</strong> 플랜 구독을 해지하시겠습니까?
          </p>
          {subscription.activeUntil && (
            <div
              className="alert alert--info"
              role="note"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
                style={{ flexShrink: 0 }}
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>
                현재 기간 만료 후 해지됩니다. 만료일:{' '}
                <strong>{formatDate(subscription.activeUntil)}</strong>
              </span>
            </div>
          )}
        </div>
        <div className="modal__footer">
          <Button variant="ghost" onClick={onClose}>
            취소
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={isLoading}>
            해지 확인
          </Button>
        </div>
      </div>
    </div>
  )
}

/* --------------------------------------------------------------------------
   구독 카드
   -------------------------------------------------------------------------- */
function SubscriptionCard({ sub }: { sub: SubscriptionSummary }) {
  const toast = useToast()
  const [showCancelModal, setShowCancelModal] = useState(false)

  const cancelSub = useCancelSubscription()
  const reactivateSub = useReactivateSubscription()

  const handleCancel = async () => {
    try {
      await cancelSub.mutateAsync(sub.subscriptionId)
      toast.success('구독 해지가 요청되었습니다.')
      setShowCancelModal(false)
    } catch (e: any) {
      toast.error(e?.message ?? '구독 해지에 실패했습니다.')
    }
  }

  const handleReactivate = async () => {
    try {
      await reactivateSub.mutateAsync(sub.subscriptionId)
      toast.success('구독 해지가 취소되었습니다.')
    } catch (e: any) {
      toast.error(e?.message ?? '구독 재활성화에 실패했습니다.')
    }
  }

  return (
    <>
      <article
        style={{
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-5)',
        }}
        aria-label={`구독: ${sub.itemTitle} - ${sub.planName}`}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 'var(--space-4)',
          }}
        >
          {/* 정보 영역 */}
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
                className={`badge ${STATUS_BADGE_CLASS[sub.status]}`}
                aria-label={`구독 상태: ${STATUS_LABEL[sub.status]}`}
              >
                {STATUS_LABEL[sub.status]}
              </span>
              <span
                style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-text-tertiary)',
                }}
              >
                {sub.planName}
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
              {sub.itemTitle}
            </h3>

            <div
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--color-text-tertiary)',
              }}
            >
              {sub.status === 'ACTIVE' && sub.nextBillingAt && (
                <span>다음 결제일: {formatDate(sub.nextBillingAt)}</span>
              )}
              {sub.status === 'CANCEL_REQUESTED' && sub.activeUntil && (
                <span>해지 예정일: {formatDate(sub.activeUntil)}</span>
              )}
              {sub.status === 'CANCELLED' && sub.activeUntil && (
                <span>해지 완료: {formatDate(sub.activeUntil)}</span>
              )}
            </div>
          </div>

          {/* 가격 + 액션 */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-end',
              gap: 'var(--space-3)',
              flexShrink: 0,
            }}
          >
            <span
              style={{
                fontSize: 'var(--font-size-base)',
                fontWeight: 'var(--font-weight-bold)',
                color: 'var(--color-text-primary)',
              }}
            >
              {formatPrice(sub.amount)}
              <span
                style={{
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 'var(--font-weight-regular)',
                  color: 'var(--color-text-tertiary)',
                  marginLeft: 2,
                }}
              >
                /월
              </span>
            </span>

            {sub.status === 'ACTIVE' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowCancelModal(true)}
              >
                구독 해지
              </Button>
            )}
            {sub.status === 'CANCEL_REQUESTED' && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleReactivate}
                loading={reactivateSub.isPending}
              >
                해지 취소
              </Button>
            )}
          </div>
        </div>
      </article>

      {showCancelModal && (
        <CancelConfirmModal
          subscription={sub}
          onConfirm={handleCancel}
          onClose={() => setShowCancelModal(false)}
          isLoading={cancelSub.isPending}
        />
      )}
    </>
  )
}

/* --------------------------------------------------------------------------
   메인 컴포넌트
   -------------------------------------------------------------------------- */
export function SubscriptionList() {
  const [page, setPage] = useState(0)
  const { data, isLoading, isError } = useSubscriptions({ page, size: 10 })

  if (isLoading) {
    return (
      <div
        style={{
          padding: 'var(--space-12)',
          textAlign: 'center',
          color: 'var(--color-text-tertiary)',
        }}
      >
        구독 내역을 불러오는 중...
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
        구독 내역을 불러올 수 없습니다.
      </div>
    )
  }

  if (!data || data.content.length === 0) {
    return (
      <div style={{ padding: 'var(--space-20)', textAlign: 'center' }}>
        <div
          style={{ fontSize: '2.5rem', marginBottom: 'var(--space-4)' }}
          aria-hidden="true"
        >
          🔄
        </div>
        <p
          style={{
            fontSize: 'var(--font-size-lg)',
            fontWeight: 'var(--font-weight-bold)',
            color: 'var(--color-text-secondary)',
            marginBottom: 'var(--space-2)',
          }}
        >
          구독 내역이 없습니다
        </p>
        <p
          style={{
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-tertiary)',
          }}
        >
          마음에 드는 크리에이터의 상품을 구독해보세요.
        </p>
      </div>
    )
  }

  return (
    <div>
      <div
        style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}
        role="list"
        aria-label="구독 목록"
      >
        {data.content.map((sub) => (
          <div key={sub.subscriptionId} role="listitem">
            <SubscriptionCard sub={sub} />
          </div>
        ))}
      </div>

      {data.totalPages > 1 && (
        <nav
          className="pagination"
          style={{ marginTop: 'var(--space-8)' }}
          aria-label="구독 내역 페이지 이동"
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
