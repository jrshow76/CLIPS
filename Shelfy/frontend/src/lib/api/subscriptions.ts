/**
 * 구독 API 함수 모음
 * API 요구사항 정의서 6. 구독 API 기반
 */

import apiClient from './client'
import type { ApiResponse, PageResponse } from '@/types/api'
import type {
  SubscribeRequest,
  SubscriptionResponse,
  CancelSubscriptionResponse,
  ReactivateSubscriptionResponse,
  SubscriptionListParams,
  SubscriptionSummary,
} from '@/types/subscription'

/** 구독 신청 (인증 필요) */
export async function subscribe(
  request: SubscribeRequest
): Promise<SubscriptionResponse> {
  const res = await apiClient.post<ApiResponse<SubscriptionResponse>>(
    '/subscriptions',
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '구독 신청에 실패했습니다.')
  }
  return res.data.data
}

/** 구독 해지 (인증 필요, 본인만) */
export async function cancelSubscription(
  subscriptionId: number
): Promise<CancelSubscriptionResponse> {
  const res = await apiClient.post<ApiResponse<CancelSubscriptionResponse>>(
    `/subscriptions/${subscriptionId}/cancel`
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '구독 해지에 실패했습니다.')
  }
  return res.data.data
}

/** 구독 해지 취소 (재활성화, 인증 필요) */
export async function reactivateSubscription(
  subscriptionId: number
): Promise<ReactivateSubscriptionResponse> {
  const res = await apiClient.post<ApiResponse<ReactivateSubscriptionResponse>>(
    `/subscriptions/${subscriptionId}/reactivate`
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '구독 재활성화에 실패했습니다.')
  }
  return res.data.data
}

/** 구독 내역 조회 (인증 필요) */
export async function fetchSubscriptions(
  params?: SubscriptionListParams
): Promise<PageResponse<SubscriptionSummary>> {
  const res = await apiClient.get<ApiResponse<PageResponse<SubscriptionSummary>>>(
    '/subscriptions',
    { params }
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '구독 내역 조회에 실패했습니다.')
  }
  return res.data.data
}
