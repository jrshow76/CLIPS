/**
 * 탐색(Browse) 페이지 (SCR-002)
 * 렌더링 전략: CSR (클라이언트 사이드)
 * - 검색, 필터, 페이지네이션을 URL searchParams로 관리
 * - TanStack Query로 서버 상태 관리
 */

'use client'

import { Suspense, useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { ItemCard, ItemCardSkeleton } from '@/components/common/ItemCard'
import { useItems, useSearchItems } from '@/hooks/useItems'
import type { ItemListParams, ItemCategory, SaleType, SortOption } from '@/types/item'

const CATEGORIES: { value: ItemCategory | 'ALL'; label: string }[] = [
  { value: 'ALL', label: '전체' },
  { value: 'TEMPLATE', label: '템플릿' },
  { value: 'FONT', label: '폰트' },
  { value: 'ICON', label: '아이콘' },
  { value: 'PHOTO', label: '사진' },
  { value: 'ILLUSTRATION', label: '일러스트' },
  { value: 'VIDEO', label: '영상' },
  { value: 'MUSIC', label: '음악' },
  { value: 'DOCUMENT', label: '문서' },
  { value: 'CODE', label: '코드' },
  { value: 'OTHER', label: '기타' },
]

const SALE_TYPES: { value: SaleType | 'ALL'; label: string }[] = [
  { value: 'ALL', label: '전체' },
  { value: 'PURCHASE', label: '구매' },
  { value: 'SUBSCRIBE', label: '구독' },
  { value: 'BOTH', label: '구매+구독' },
]

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'latest', label: '최신순' },
  { value: 'popular', label: '인기순' },
  { value: 'lowPrice', label: '낮은 가격순' },
  { value: 'highPrice', label: '높은 가격순' },
]

const PAGE_SIZE = 20

export default function BrowsePage() {
  return (
    <Suspense>
      <BrowseContent />
    </Suspense>
  )
}

function BrowseContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // URL 파라미터에서 초기 상태 복원
  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') ?? '')
  const [inputValue, setInputValue] = useState(searchParams.get('q') ?? '')
  const [category, setCategory] = useState<ItemCategory | 'ALL'>(
    (searchParams.get('category') as ItemCategory) ?? 'ALL'
  )
  const [saleType, setSaleType] = useState<SaleType | 'ALL'>(
    (searchParams.get('saleType') as SaleType) ?? 'ALL'
  )
  const [sort, setSort] = useState<SortOption>(
    (searchParams.get('sort') as SortOption) ?? 'latest'
  )
  const [page, setPage] = useState(Number(searchParams.get('page') ?? 0))

  // URL searchParams 동기화
  useEffect(() => {
    const params = new URLSearchParams()
    if (searchQuery) params.set('q', searchQuery)
    if (category !== 'ALL') params.set('category', category)
    if (saleType !== 'ALL') params.set('saleType', saleType)
    if (sort !== 'latest') params.set('sort', sort)
    if (page > 0) params.set('page', String(page))
    router.replace(`/browse?${params.toString()}`, { scroll: false })
  }, [searchQuery, category, saleType, sort, page, router])

  const listParams: ItemListParams = {
    ...(category !== 'ALL' && { category }),
    ...(saleType !== 'ALL' && { saleType }),
    sort,
    page,
    size: PAGE_SIZE,
  }

  const isSearchMode = searchQuery.trim().length > 0

  const { data: browseData, isLoading: isBrowseLoading } = useItems(
    isSearchMode ? undefined : listParams
  )
  const { data: searchData, isLoading: isSearchLoading } = useSearchItems(
    {
      q: searchQuery,
      ...(category !== 'ALL' && { category }),
      ...(saleType !== 'ALL' && { saleType }),
      page,
      size: PAGE_SIZE,
    },
    isSearchMode
  )

  const data = isSearchMode ? searchData : browseData
  const isLoading = isSearchMode ? isSearchLoading : isBrowseLoading

  const items = data?.content ?? []
  const totalPages = data?.totalPages ?? 0
  const totalElements = data?.totalElements ?? 0

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSearchQuery(inputValue.trim())
    setPage(0)
  }

  const handleFilterChange = useCallback(() => {
    setPage(0)
  }, [])

  function renderPagination() {
    if (totalPages <= 1) return null
    const pages = Array.from({ length: Math.min(totalPages, 10) }, (_, i) => i)
    return (
      <nav className="pagination" aria-label="페이지 탐색">
        <button
          className={`pagination__item ${page === 0 ? 'pagination__item--disabled' : ''}`}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
          aria-label="이전 페이지"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        {pages.map((p) => (
          <button
            key={p}
            className={`pagination__item ${p === page ? 'pagination__item--active' : ''}`}
            onClick={() => setPage(p)}
            aria-label={`${p + 1}페이지`}
            aria-current={p === page ? 'page' : undefined}
          >
            {p + 1}
          </button>
        ))}
        <button
          className={`pagination__item ${page >= totalPages - 1 ? 'pagination__item--disabled' : ''}`}
          onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
          disabled={page >= totalPages - 1}
          aria-label="다음 페이지"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>
      </nav>
    )
  }

  return (
    <main className="page-body">
      {/* 검색 헤더 */}
      <div
        className="search-header"
        style={{
          background: 'var(--color-bg-surface)',
          borderBottom: '1px solid var(--color-border-default)',
          padding: 'var(--space-6) 0',
        }}
      >
        <div className="container">
          <form
            onSubmit={handleSearchSubmit}
            style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}
            role="search"
            aria-label="상품 검색"
          >
            <input
              type="search"
              className="form-input"
              placeholder="찾고 있는 콘텐츠를 검색하세요..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              aria-label="검색어 입력"
              style={{ flex: 1, maxWidth: 600 }}
            />
            <button type="submit" className="btn btn--primary">
              검색
            </button>
          </form>

          {/* 검색 결과 정보 */}
          {isSearchMode && !isLoading && (
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-tertiary)' }}>
              <strong style={{ color: 'var(--color-text-primary)' }}>
                &ldquo;{searchQuery}&rdquo;
              </strong>
              {' '}검색 결과{' '}
              <strong style={{ color: 'var(--color-primary)' }}>
                {totalElements.toLocaleString()}
              </strong>
              건
            </p>
          )}
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="container" style={{ paddingTop: 'var(--space-8)', paddingBottom: 'var(--space-20)' }}>
        <div
          className="browse-layout"
          style={{ display: 'flex', gap: 'var(--space-8)', alignItems: 'flex-start' }}
        >
          {/* 필터 사이드바 */}
          <aside
            className="filter-sidebar"
            style={{ width: 260, flexShrink: 0 }}
            aria-label="필터"
          >
            {/* 카테고리 필터 */}
            <div className="filter-group" style={{ marginBottom: 'var(--space-6)' }}>
              <h3
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text-secondary)',
                  marginBottom: 'var(--space-3)',
                }}
              >
                카테고리
              </h3>
              <ul style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                {CATEGORIES.map((cat) => (
                  <li key={cat.value}>
                    <button
                      className={`tag ${category === cat.value ? 'tag--active' : ''}`}
                      style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 'var(--radius-md)' }}
                      onClick={() => {
                        setCategory(cat.value as ItemCategory | 'ALL')
                        handleFilterChange()
                      }}
                      aria-pressed={category === cat.value}
                    >
                      {cat.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {/* 판매 유형 필터 */}
            <div className="filter-group" style={{ marginBottom: 'var(--space-6)' }}>
              <h3
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text-secondary)',
                  marginBottom: 'var(--space-3)',
                }}
              >
                판매 유형
              </h3>
              <ul style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                {SALE_TYPES.map((type) => (
                  <li key={type.value}>
                    <button
                      className={`tag ${saleType === type.value ? 'tag--active' : ''}`}
                      style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 'var(--radius-md)' }}
                      onClick={() => {
                        setSaleType(type.value as SaleType | 'ALL')
                        handleFilterChange()
                      }}
                      aria-pressed={saleType === type.value}
                    >
                      {type.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </aside>

          {/* 상품 목록 */}
          <div className="browse-content" style={{ flex: 1, minWidth: 0 }}>
            {/* 정렬 툴바 */}
            <div
              className="browse-toolbar-row"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 'var(--space-6)',
              }}
            >
              {!isLoading && (
                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-tertiary)' }}>
                  총 <strong style={{ color: 'var(--color-text-primary)' }}>
                    {totalElements.toLocaleString()}
                  </strong>개
                </p>
              )}
              <select
                className="form-select"
                value={sort}
                onChange={(e) => {
                  setSort(e.target.value as SortOption)
                  setPage(0)
                }}
                aria-label="정렬 기준 선택"
                style={{ width: 'auto', minWidth: 130 }}
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 상품 그리드 */}
            {isLoading ? (
              <div className="browse-grid grid grid--3">
                {Array.from({ length: 9 }).map((_, i) => (
                  <ItemCardSkeleton key={i} />
                ))}
              </div>
            ) : items.length > 0 ? (
              <div className="browse-grid grid grid--3">
                {items.map((item) => (
                  <ItemCard key={item.itemId} item={item} />
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-state__icon" aria-hidden="true">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="11" cy="11" r="8" />
                    <path d="M21 21l-4.35-4.35" />
                  </svg>
                </div>
                <p className="empty-state__title">
                  {isSearchMode ? '검색 결과가 없어요' : '상품이 없어요'}
                </p>
                <p className="empty-state__desc">
                  {isSearchMode
                    ? '다른 검색어나 필터를 시도해보세요.'
                    : '아직 등록된 상품이 없습니다.'}
                </p>
              </div>
            )}

            {/* 페이지네이션 */}
            {renderPagination()}
          </div>
        </div>
      </div>
    </main>
  )
}
