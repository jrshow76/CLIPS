/**
 * 주문 API 함수 모음
 * API 요구사항 정의서 5. 주문/결제 API 기반
 */

import apiClient from './client'
import type { ApiResponse, PageResponse } from '@/types/api'

export type OrderStatus =
  | 'PENDING'
  | 'PAID'
  | 'CANCELLED'
  | 'REFUND_REQUESTED'
  | 'REFUNDED'

export interface OrderItem {
  itemId: number
  title: string
  thumbnailUrl?: string
  price: number
}

export interface OrderSummary {
  orderId: number
  item: OrderItem
  status: OrderStatus
  paidAmount: number
  createdAt: string
  paidAt?: string
}

export interface OrderDetail extends OrderSummary {
  pgOrderId: string
  paymentMethod?: string
  refundedAt?: string
  refundReason?: string
}

export interface CreateOrderRequest {
  itemId: number
  paymentMethod: 'CARD' | 'KAKAO_PAY' | 'NAVER_PAY'
  pgOrderId: string
}

export interface CreateOrderResponse {
  orderId: number
  pgOrderId: string
  status: OrderStatus
  paidAmount: number
  paidAt: string
}

export interface RequestRefundRequest {
  reason: string
}

export interface RequestRefundResponse {
  orderId: number
  status: OrderStatus
  refundRequestedAt: string
}

export interface OrderListParams {
  status?: OrderStatus | 'ALL'
  page?: number
  size?: number
}

/** 주문 생성 (인증 필요) */
export async function createOrder(
  request: CreateOrderRequest
): Promise<CreateOrderResponse> {
  const res = await apiClient.post<ApiResponse<CreateOrderResponse>>(
    '/orders',
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '주문 생성에 실패했습니다.')
  }
  return res.data.data
}

/** 주문 목록 조회 (인증 필요) */
export async function fetchOrders(
  params?: OrderListParams
): Promise<PageResponse<OrderSummary>> {
  const res = await apiClient.get<ApiResponse<PageResponse<OrderSummary>>>(
    '/orders',
    { params }
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '주문 목록 조회에 실패했습니다.')
  }
  return res.data.data
}

/** 주문 상세 조회 (인증 필요) */
export async function fetchOrder(orderId: number): Promise<OrderDetail> {
  const res = await apiClient.get<ApiResponse<OrderDetail>>(
    `/orders/${orderId}`
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '주문 상세 조회에 실패했습니다.')
  }
  return res.data.data
}

/** 환불 요청 (인증 필요, 본인만) */
export async function requestRefund(
  orderId: number,
  request: RequestRefundRequest
): Promise<RequestRefundResponse> {
  const res = await apiClient.post<ApiResponse<RequestRefundResponse>>(
    `/orders/${orderId}/refund`,
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '환불 요청에 실패했습니다.')
  }
  return res.data.data
}
