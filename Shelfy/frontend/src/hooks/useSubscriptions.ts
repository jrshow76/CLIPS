/**
 * 구독 TanStack Query 훅 모음
 */

'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  subscribe,
  cancelSubscription,
  reactivateSubscription,
  fetchSubscriptions,
} from '@/lib/api/subscriptions'
import type { SubscribeRequest, SubscriptionListParams } from '@/types/subscription'

// Query Key 상수화
export const subscriptionQueryKeys = {
  all: ['subscriptions'] as const,
  lists: () => [...subscriptionQueryKeys.all, 'list'] as const,
  list: (params?: SubscriptionListParams) =>
    [...subscriptionQueryKeys.lists(), params] as const,
} as const

/** 구독 내역 조회 */
export function useSubscriptions(params?: SubscriptionListParams) {
  return useQuery({
    queryKey: subscriptionQueryKeys.list(params),
    queryFn: () => fetchSubscriptions(params),
    staleTime: 30 * 1000,
  })
}

/** 구독 신청 뮤테이션 */
export function useSubscribe() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: SubscribeRequest) => subscribe(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: subscriptionQueryKeys.lists() })
    },
  })
}

/** 구독 해지 뮤테이션 */
export function useCancelSubscription() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (subscriptionId: number) => cancelSubscription(subscriptionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: subscriptionQueryKeys.lists() })
    },
  })
}

/** 구독 해지 취소(재활성화) 뮤테이션 */
export function useReactivateSubscription() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (subscriptionId: number) =>
      reactivateSubscription(subscriptionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: subscriptionQueryKeys.lists() })
    },
  })
}
