/**
 * 구독 도메인 타입 정의
 * API 요구사항 정의서 6. 구독 API 기반
 */

export type SubscriptionStatus =
  | 'ACTIVE'
  | 'CANCEL_REQUESTED'
  | 'CANCELLED'

/** 구독 신청 요청 */
export interface SubscribeRequest {
  itemId: number
  planId: number
  paymentMethod: string
}

/** 구독 신청 응답 */
export interface SubscriptionResponse {
  subscriptionId: number
  itemId: number
  itemTitle: string
  planName: string
  period: 'MONTHLY' | 'YEARLY'
  amount: number
  status: SubscriptionStatus
  startedAt: string
  nextBillingAt: string
}

/** 구독 해지 응답 */
export interface CancelSubscriptionResponse {
  subscriptionId: number
  status: SubscriptionStatus
  cancelledAt: string
  activeUntil: string
}

/** 구독 재활성화 응답 */
export interface ReactivateSubscriptionResponse {
  subscriptionId: number
  status: SubscriptionStatus
}

/** 구독 내역 조회 쿼리 파라미터 */
export interface SubscriptionListParams {
  status?: 'ALL' | SubscriptionStatus
  page?: number
  size?: number
}

/** 구독 내역 아이템 */
export interface SubscriptionSummary {
  subscriptionId: number
  itemTitle: string
  planName: string
  amount: number
  status: SubscriptionStatus
  nextBillingAt?: string
  activeUntil?: string
}
