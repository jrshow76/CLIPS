/**
 * 사용자/프로필 도메인 타입 정의
 * API 요구사항 정의서 7. 사용자 프로필 API 기반
 */

import type { ItemSummary } from './item'
import type { PageResponse } from './api'

/** 셀러 공개 프로필 응답 */
export interface SellerProfile {
  userId: number
  nickname: string
  bio?: string
  profileImageUrl?: string
  itemCount: number
  subscriberCount: number
  joinedAt: string
  items: PageResponse<ItemSummary>
}

/** 내 프로필 응답 (공개 프로필 + 비공개 필드) */
export interface MyProfile extends SellerProfile {
  email: string
  emailVerified: boolean
  agreeMarketing: boolean
  createdAt: string
}

/** 내 프로필 수정 요청 */
export interface UpdateProfileRequest {
  nickname?: string
  bio?: string
  profileImageId?: string
}

/** 월별 수익 */
export interface MonthlyRevenue {
  month: string
  revenue: number
}

/** 상품별 수익 */
export interface ItemRevenue {
  itemId: number
  itemTitle: string
  purchaseCount: number
  subscriptionCount: number
  revenue: number
}

/** 수익 현황 응답 */
export interface RevenueResponse {
  totalRevenue: number
  totalFee: number
  netRevenue: number
  activeSubscribers: number
  monthlyRevenue: MonthlyRevenue[]
  itemRevenue: ItemRevenue[]
}
