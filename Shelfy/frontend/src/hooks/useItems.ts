/**
 * 상품 TanStack Query 훅 모음
 * DevLead 개발 표준 6.4 TanStack Query 사용 규칙 기반
 */

'use client'

import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
} from '@tanstack/react-query'
import {
  fetchItems,
  searchItems,
  fetchItemDetail,
  fetchMyItems,
  createItem,
  updateItem,
  deleteItem,
  updateItemStatus,
} from '@/lib/api/items'
import type {
  ItemListParams,
  ItemSearchParams,
  MyItemListParams,
  CreateItemRequest,
  ItemStatus,
} from '@/types/item'

// Query Key 상수화 (캐시 무효화 일관성 확보)
export const itemQueryKeys = {
  all: ['items'] as const,
  lists: () => [...itemQueryKeys.all, 'list'] as const,
  list: (params?: ItemListParams) => [...itemQueryKeys.lists(), params] as const,
  search: (params: ItemSearchParams) =>
    [...itemQueryKeys.all, 'search', params] as const,
  detail: (itemId: number) =>
    [...itemQueryKeys.all, 'detail', itemId] as const,
  myItems: () => [...itemQueryKeys.all, 'my'] as const,
  myList: (params?: MyItemListParams) =>
    [...itemQueryKeys.myItems(), params] as const,
} as const

/** 상품 목록 조회 */
export function useItems(params?: ItemListParams) {
  return useQuery({
    queryKey: itemQueryKeys.list(params),
    queryFn: () => fetchItems(params),
    staleTime: 60 * 1000, // 1분
  })
}

/** 상품 목록 무한 스크롤 */
export function useInfiniteItems(baseParams?: Omit<ItemListParams, 'page'>) {
  return useInfiniteQuery({
    queryKey: [...itemQueryKeys.lists(), 'infinite', baseParams],
    queryFn: ({ pageParam }) =>
      fetchItems({ ...baseParams, page: pageParam as number, size: 20 }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      if (lastPage.last) return undefined
      return lastPage.page + 1
    },
    staleTime: 60 * 1000,
  })
}

/** 상품 검색 */
export function useSearchItems(params: ItemSearchParams, enabled = true) {
  return useQuery({
    queryKey: itemQueryKeys.search(params),
    queryFn: () => searchItems(params),
    enabled: enabled && params.q.length > 0,
    staleTime: 30 * 1000,
  })
}

/** 상품 상세 조회 */
export function useItem(itemId: number) {
  return useQuery({
    queryKey: itemQueryKeys.detail(itemId),
    queryFn: () => fetchItemDetail(itemId),
    enabled: !!itemId,
    staleTime: 60 * 1000,
  })
}

/** 내 상품 목록 조회 */
export function useMyItems(params?: MyItemListParams) {
  return useQuery({
    queryKey: itemQueryKeys.myList(params),
    queryFn: () => fetchMyItems(params),
    staleTime: 30 * 1000,
  })
}

/** 상품 등록 뮤테이션 */
export function useCreateItem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: CreateItemRequest) => createItem(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.myItems() })
    },
  })
}

/** 상품 수정 뮤테이션 */
export function useUpdateItem(itemId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: Partial<CreateItemRequest>) =>
      updateItem(itemId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.detail(itemId) })
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.myItems() })
    },
  })
}

/** 상품 삭제 뮤테이션 */
export function useDeleteItem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (itemId: number) => deleteItem(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.myItems() })
    },
  })
}

/** 상품 상태 변경 뮤테이션 */
export function useUpdateItemStatus(itemId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (status: ItemStatus) => updateItemStatus(itemId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.detail(itemId) })
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.myItems() })
    },
  })
}
