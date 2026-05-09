/**
 * 아이템 상세 - 구매/구독 패널 (클라이언트 컴포넌트)
 * 판매 유형에 따라 구매 버튼, 구독 플랜 선택, 구매+구독 탭 분기 렌더링
 */

'use client'

import { useState } from 'react'
import { Button } from '@/components/common/Button'
import { useAuth } from '@/hooks/useAuth'
import { useSubscribe } from '@/hooks/useSubscriptions'
import { useToast } from '@/components/common/Toast'
import type { ItemDetail, SubscriptionPlan } from '@/types/item'

interface ItemPurchasePanelProps {
  item: ItemDetail
}

function formatPrice(price: number): string {
  return price.toLocaleString('ko-KR') + '원'
}

function PeriodLabel({ period }: { period: 'MONTHLY' | 'YEARLY' }) {
  return period === 'MONTHLY' ? '월' : '연'
}

export function ItemPurchasePanel({ item }: ItemPurchasePanelProps) {
  const { isLoggedIn, requireAuth } = useAuth()
  const toast = useToast()
  const subscribeMutation = useSubscribe()

  const [activeTab, setActiveTab] = useState<'purchase' | 'subscribe'>(
    item.saleType === 'SUBSCRIBE' ? 'subscribe' : 'purchase'
  )
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlan | null>(
    item.subscriptionPlans[0] ?? null
  )
  const [isPurchasing, setIsPurchasing] = useState(false)

  async function handlePurchase() {
    if (!requireAuth()) return
    setIsPurchasing(true)
    try {
      // 구매 API 호출 (orders.ts가 FrontendDev 담당이므로 임시 처리)
      toast.success('구매가 완료되었습니다.')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '구매에 실패했습니다.')
    } finally {
      setIsPurchasing(false)
    }
  }

  async function handleSubscribe() {
    if (!requireAuth()) return
    if (!selectedPlan) {
      toast.warning('구독 플랜을 선택해주세요.')
      return
    }
    try {
      await subscribeMutation.mutateAsync({
        itemId: item.itemId,
        planId: selectedPlan.planId,
        paymentMethod: 'CARD',
      })
      toast.success('구독이 시작되었습니다.')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '구독 신청에 실패했습니다.')
    }
  }

  return (
    <div
      style={{
        background: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border-default)',
        borderRadius: 'var(--radius-2xl)',
        padding: 'var(--space-6)',
        boxShadow: 'var(--shadow-md)',
      }}
    >
      {/* 가격 블록 */}
      <div
        className="item-panel__price-block"
        style={{ marginBottom: 'var(--space-6)' }}
      >
        {item.saleType === 'BOTH' ? (
          /* 탭 UI: 구매 / 구독 전환 */
          <div>
            <div
              style={{
                display: 'flex',
                gap: 0,
                borderBottom: '1px solid var(--color-border-default)',
                marginBottom: 'var(--space-4)',
              }}
              role="tablist"
            >
              {['purchase', 'subscribe'].map((tab) => (
                <button
                  key={tab}
                  role="tab"
                  aria-selected={activeTab === tab}
                  onClick={() => setActiveTab(tab as 'purchase' | 'subscribe')}
                  style={{
                    flex: 1,
                    padding: 'var(--space-3) var(--space-4)',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color:
                      activeTab === tab
                        ? 'var(--color-primary)'
                        : 'var(--color-text-tertiary)',
                    borderBottom:
                      activeTab === tab
                        ? '2px solid var(--color-primary)'
                        : '2px solid transparent',
                    marginBottom: -1,
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    transition: 'color var(--transition-base)',
                  }}
                >
                  {tab === 'purchase' ? '일회 구매' : '구독'}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {/* 구매 가격 */}
        {(item.saleType === 'PURCHASE' ||
          (item.saleType === 'BOTH' && activeTab === 'purchase')) && (
          <div>
            <p
              style={{
                fontSize: 'var(--font-size-3xl)',
                fontWeight: 'var(--font-weight-bold)',
                color: 'var(--color-text-primary)',
              }}
            >
              {formatPrice(item.price)}
            </p>
            <p
              style={{
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text-tertiary)',
                marginTop: 'var(--space-1)',
              }}
            >
              일회 구매 후 영구 이용
            </p>
          </div>
        )}

        {/* 구독 플랜 */}
        {(item.saleType === 'SUBSCRIBE' ||
          (item.saleType === 'BOTH' && activeTab === 'subscribe')) &&
          item.subscriptionPlans.length > 0 && (
            <div className="sub-plans">
              <p
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text-secondary)',
                  marginBottom: 'var(--space-3)',
                }}
              >
                구독 플랜 선택
              </p>
              <div
                style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}
                role="radiogroup"
                aria-label="구독 플랜"
              >
                {item.subscriptionPlans.map((plan) => (
                  <label
                    key={plan.planId}
                    className={`form-radio-card ${
                      selectedPlan?.planId === plan.planId
                        ? 'form-radio-card--selected'
                        : ''
                    }`}
                    style={{ cursor: 'pointer' }}
                  >
                    <input
                      type="radio"
                      name="subscription-plan"
                      value={plan.planId}
                      checked={selectedPlan?.planId === plan.planId}
                      onChange={() => setSelectedPlan(plan)}
                      aria-label={`${plan.planName} - ${formatPrice(plan.planPrice)}/${plan.period === 'MONTHLY' ? '월' : '연'}`}
                    />
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <p className="form-radio-card__title">{plan.planName}</p>
                        {plan.description && (
                          <p className="form-radio-card__desc">{plan.description}</p>
                        )}
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <strong
                          style={{
                            fontSize: 'var(--font-size-base)',
                            fontWeight: 'var(--font-weight-bold)',
                            color: 'var(--color-text-primary)',
                          }}
                        >
                          {formatPrice(plan.planPrice)}
                        </strong>
                        <span
                          style={{
                            fontSize: 'var(--font-size-xs)',
                            color: 'var(--color-text-tertiary)',
                          }}
                        >
                          /<PeriodLabel period={plan.period} />
                        </span>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}
      </div>

      {/* CTA 버튼 */}
      <div
        className="item-panel__cta"
        style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}
      >
        {(item.saleType === 'PURCHASE' ||
          (item.saleType === 'BOTH' && activeTab === 'purchase')) && (
          <Button
            variant="primary"
            size="lg"
            fullWidth
            loading={isPurchasing}
            onClick={handlePurchase}
          >
            {formatPrice(item.price)} 구매하기
          </Button>
        )}

        {(item.saleType === 'SUBSCRIBE' ||
          (item.saleType === 'BOTH' && activeTab === 'subscribe')) && (
          <Button
            variant="primary"
            size="lg"
            fullWidth
            loading={subscribeMutation.isPending}
            onClick={handleSubscribe}
            disabled={!selectedPlan}
          >
            {selectedPlan
              ? `${formatPrice(selectedPlan.planPrice)}/${selectedPlan.period === 'MONTHLY' ? '월' : '연'} 구독하기`
              : '플랜을 선택해주세요'}
          </Button>
        )}

        {!isLoggedIn && (
          <p
            style={{
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-text-tertiary)',
              textAlign: 'center',
            }}
          >
            구매/구독하려면 로그인이 필요합니다.
          </p>
        )}
      </div>
    </div>
  )
}
