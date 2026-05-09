/**
 * 상품 API 함수 모음
 * API 요구사항 정의서 3. 상품 API, 4. 탐색 및 검색 API 기반
 */

import apiClient from './client'
import type { ApiResponse, PageResponse } from '@/types/api'
import type {
  ItemDetail,
  ItemSummary,
  MyItemSummary,
  CreateItemRequest,
  CreateItemResponse,
  UpdateItemResponse,
  UpdateItemStatusRequest,
  ItemListParams,
  ItemSearchParams,
  MyItemListParams,
  ItemStatus,
} from '@/types/item'

/** 상품 목록 탐색 (공개) */
export async function fetchItems(
  params?: ItemListParams
): Promise<PageResponse<ItemSummary>> {
  const res = await apiClient.get<ApiResponse<PageResponse<ItemSummary>>>(
    '/items',
    { params }
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '상품 목록 조회에 실패했습니다.')
  }
  return res.data.data
}

/** 상품 검색 (공개) */
export async function searchItems(
  params: ItemSearchParams
): Promise<PageResponse<ItemSummary>> {
  const res = await apiClient.get<ApiResponse<PageResponse<ItemSummary>>>(
    '/items/search',
    { params }
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '상품 검색에 실패했습니다.')
  }
  return res.data.data
}

/** 상품 상세 조회 (공개, DRAFT는 본인만) */
export async function fetchItemDetail(itemId: number): Promise<ItemDetail> {
  const res = await apiClient.get<ApiResponse<ItemDetail>>(`/items/${itemId}`)
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '상품 상세 조회에 실패했습니다.')
  }
  return res.data.data
}

/** 내 상품 목록 조회 (인증 필요) */
export async function fetchMyItems(
  params?: MyItemListParams
): Promise<PageResponse<MyItemSummary>> {
  const res = await apiClient.get<ApiResponse<PageResponse<MyItemSummary>>>(
    '/items/my',
    { params }
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '내 상품 목록 조회에 실패했습니다.')
  }
  return res.data.data
}

/** 상품 등록 (인증 필요) */
export async function createItem(
  request: CreateItemRequest
): Promise<CreateItemResponse> {
  const res = await apiClient.post<ApiResponse<CreateItemResponse>>(
    '/items',
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '상품 등록에 실패했습니다.')
  }
  return res.data.data
}

/** 상품 수정 (인증 필요, 본인만) */
export async function updateItem(
  itemId: number,
  request: Partial<CreateItemRequest>
): Promise<UpdateItemResponse> {
  const res = await apiClient.put<ApiResponse<UpdateItemResponse>>(
    `/items/${itemId}`,
    request
  )
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '상품 수정에 실패했습니다.')
  }
  return res.data.data
}

/** 상품 삭제 (인증 필요, 본인만, 204 No Content) */
export async function deleteItem(itemId: number): Promise<void> {
  await apiClient.delete(`/items/${itemId}`)
}

/** 상품 상태 변경 (공개/비공개, 인증 필요) */
export async function updateItemStatus(
  itemId: number,
  status: ItemStatus
): Promise<{ itemId: number; status: ItemStatus }> {
  const request: UpdateItemStatusRequest = { status }
  const res = await apiClient.patch<
    ApiResponse<{ itemId: number; status: ItemStatus }>
  >(`/items/${itemId}/status`, request)
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '상태 변경에 실패했습니다.')
  }
  return res.data.data
}
