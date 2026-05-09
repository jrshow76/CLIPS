/**
 * 아이템(상품) 도메인 타입 정의
 * API 요구사항 정의서 3. 상품 API, 4. 탐색 및 검색 API 기반
 */

export type SaleType = 'PURCHASE' | 'SUBSCRIBE' | 'BOTH'
export type ItemStatus = 'DRAFT' | 'PUBLISHED' | 'DELETED'
export type ItemCategory =
  | 'TEMPLATE'
  | 'FONT'
  | 'ICON'
  | 'PHOTO'
  | 'ILLUSTRATION'
  | 'VIDEO'
  | 'MUSIC'
  | 'DOCUMENT'
  | 'CODE'
  | 'OTHER'
export type SubscriptionPeriod = 'MONTHLY' | 'YEARLY'
export type SortOption = 'latest' | 'popular' | 'lowPrice' | 'highPrice'

/** 구독 플랜 (상품 등록/수정 요청 시) */
export interface SubscriptionPlanRequest {
  planName: string
  period: SubscriptionPeriod
  planPrice: number
  description?: string
}

/** 구독 플랜 (응답) */
export interface SubscriptionPlan {
  planId: number
  planName: string
  period: SubscriptionPeriod
  planPrice: number
  description?: string
}

/** 상품 이미지 */
export interface ItemImage {
  imageId: string
  url: string
  isThumbnail: boolean
}

/** 셀러 요약 정보 (상품 카드/상세에 포함) */
export interface SellerSummary {
  userId: number
  nickname: string
  profileImageUrl?: string
  itemCount: number
}

/** 상품 목록 조회 쿼리 파라미터 */
export interface ItemListParams {
  category?: ItemCategory
  saleType?: SaleType
  minPrice?: number
  maxPrice?: number
  sort?: SortOption
  page?: number
  size?: number
}

/** 상품 검색 쿼리 파라미터 */
export interface ItemSearchParams {
  q: string
  category?: ItemCategory
  saleType?: SaleType
  page?: number
  size?: number
}

/** 상품 목록 아이템 (피드/검색 결과에 사용) */
export interface ItemSummary {
  itemId: number
  title: string
  price: number
  saleType: SaleType
  thumbnailUrl?: string
  seller: Pick<SellerSummary, 'userId' | 'nickname' | 'profileImageUrl'>
}

/** 상품 상세 응답 */
export interface ItemDetail {
  itemId: number
  title: string
  description: string
  category: ItemCategory
  saleType: SaleType
  price: number
  subscriptionPlans: SubscriptionPlan[]
  images: ItemImage[]
  tags: string[]
  status: ItemStatus
  viewCount: number
  seller: SellerSummary
  createdAt: string
  updatedAt: string
}

/** 상품 등록/수정 요청 */
export interface CreateItemRequest {
  title: string
  description: string
  category: ItemCategory
  saleType: SaleType
  price: number
  subscriptionPlans?: SubscriptionPlanRequest[]
  imageIds: string[]
  thumbnailIndex: number
  tags?: string[]
  status: ItemStatus
}

/** 상품 등록 응답 */
export interface CreateItemResponse {
  itemId: number
}

/** 상품 수정 응답 */
export interface UpdateItemResponse {
  itemId: number
  updatedAt: string
}

/** 내 상품 목록 쿼리 파라미터 */
export interface MyItemListParams {
  status?: 'ALL' | ItemStatus
  page?: number
  size?: number
  sort?: 'createdAt' | 'title' | 'price'
  order?: 'ASC' | 'DESC'
}

/** 내 상품 목록 아이템 */
export interface MyItemSummary {
  itemId: number
  title: string
  status: ItemStatus
  price: number
  thumbnailUrl?: string
  createdAt: string
}

/** 상품 상태 변경 요청 */
export interface UpdateItemStatusRequest {
  status: ItemStatus
}
