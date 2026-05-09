/**
 * 주문 TanStack Query 훅 모음
 * DevLead 개발 표준 6.4 TanStack Query 사용 규칙 기반
 */

'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  createOrder,
  fetchOrders,
  fetchOrder,
  requestRefund,
} from '@/lib/api/orders'
import type {
  CreateOrderRequest,
  RequestRefundRequest,
  OrderListParams,
} from '@/lib/api/orders'

// Query Key 상수화 (캐시 무효화 일관성 확보)
export const orderQueryKeys = {
  all: ['orders'] as const,
  lists: () => [...orderQueryKeys.all, 'list'] as const,
  list: (params?: OrderListParams) => [...orderQueryKeys.lists(), params] as const,
  detail: (orderId: number) => [...orderQueryKeys.all, 'detail', orderId] as const,
} as const

/** 주문 목록 조회 */
export function useOrders(params?: OrderListParams) {
  return useQuery({
    queryKey: orderQueryKeys.list(params),
    queryFn: () => fetchOrders(params),
    staleTime: 30 * 1000,
  })
}

/** 주문 상세 조회 */
export function useOrder(orderId: number) {
  return useQuery({
    queryKey: orderQueryKeys.detail(orderId),
    queryFn: () => fetchOrder(orderId),
    enabled: !!orderId,
    staleTime: 30 * 1000,
  })
}

/** 주문 생성 뮤테이션 */
export function useCreateOrder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: CreateOrderRequest) => createOrder(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.lists() })
    },
  })
}

/** 환불 요청 뮤테이션 */
export function useRequestRefund(orderId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: RequestRefundRequest) =>
      requestRefund(orderId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.detail(orderId) })
      queryClient.invalidateQueries({ queryKey: orderQueryKeys.lists() })
    },
  })
}
