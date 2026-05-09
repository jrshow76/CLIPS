/**
 * 셀러 대시보드 API 함수 모음
 * API 요구사항 정의서 9. 셀러 대시보드 API 기반
 */

import apiClient from './client'
import type { ApiResponse } from '@/types/api'
import type { RevenueResponse } from '@/types/user'

export interface SellerStats {
  totalRevenue: number
  totalOrders: number
  activeSubscribers: number
  totalItems: number
  publishedItems: number
  draftItems: number
}

export interface SellerRevenueParams {
  from?: string
  to?: string
  period?: 'MONTHLY' | 'YEARLY'
}

export interface SellerProfileResponse {
  userId: number
  nickname: string
  bio?: string
  profileImageUrl?: string
  itemCount: number
  subscriberCount: number
  joinedAt: string
}

/** 셀러 통계 조회 (인증 필요) */
export async function fetchSellerStats(): Promise<SellerStats> {
  const res = await apiClient.get<ApiResponse<SellerStats>>(
    '/seller/stats'
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '셀러 통계 조회에 실패했습니다.')
  }
  return res.data.data
}

/** 셀러 수익 현황 조회 (인증 필요) */
export async function fetchSellerRevenue(
  params?: SellerRevenueParams
): Promise<RevenueResponse> {
  const res = await apiClient.get<ApiResponse<RevenueResponse>>(
    '/seller/revenue',
    { params }
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '수익 현황 조회에 실패했습니다.')
  }
  return res.data.data
}

/** 셀러 공개 프로필 조회 (전체 공개) */
export async function fetchSellerProfile(
  nickname: string
): Promise<SellerProfileResponse> {
  const res = await apiClient.get<ApiResponse<SellerProfileResponse>>(
    `/seller/profile/${nickname}`
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '셀러 프로필 조회에 실패했습니다.')
  }
  return res.data.data
}
