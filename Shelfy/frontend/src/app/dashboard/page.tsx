'use client'

/**
 * SCR-020 셀러 대시보드 (CSR)
 * 총 판매액, 주문 수, 활성 구독자 수 통계 카드 + 내 아이템 목록
 * 04_my-shelf.html 구조 기반
 */

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Button } from '@/components/common/Button'
import { useToast } from '@/components/common/Toast'
import { useAuth } from '@/hooks/useAuth'
import { useMyItems, useDeleteItem } from '@/hooks/useItems'
import { useQueryClient, useQuery } from '@tanstack/react-query'
import { fetchSellerStats } from '@/lib/api/seller'
import { updateItemStatus } from '@/lib/api/items'
import { itemQueryKeys } from '@/hooks/useItems'
import type { MyItemSummary, ItemStatus } from '@/types/item'

/* --------------------------------------------------------------------------
   셀러 통계 훅 (인라인 정의 - seller 전용 훅은 별도 파일로 분리 가능)
   -------------------------------------------------------------------------- */
function useSellerStats() {
  return useQuery({
    queryKey: ['seller', 'stats'],
    queryFn: fetchSellerStats,
    staleTime: 60 * 1000,
  })
}

/* --------------------------------------------------------------------------
   통계 카드 컴포넌트
   -------------------------------------------------------------------------- */
interface StatCardProps {
  label: string
  value: string | number
  icon: React.ReactNode
  color?: string
}

function StatCard({ label, value, icon, color = 'var(--color-primary)' }: StatCardProps) {
  return (
    <div
      style={{
        background: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border-default)',
        borderRadius: 'var(--radius-xl)',
        padding: 'var(--space-6)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-4)',
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 'var(--radius-lg)',
          backgroundColor: `${color}18`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          color,
        }}
        aria-hidden="true"
      >
        {icon}
      </div>
      <div>
        <p
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-text-tertiary)',
            marginBottom: 'var(--space-1)',
          }}
        >
          {label}
        </p>
        <p
          style={{
            fontSize: 'var(--font-size-2xl)',
            fontWeight: 'var(--font-weight-bold)',
            color: 'var(--color-text-primary)',
            lineHeight: 1,
          }}
        >
          {value}
        </p>
      </div>
    </div>
  )
}

function formatPrice(price: number): string {
  if (price >= 10000) {
    return (price / 10000).toFixed(1).replace('.0', '') + '만원'
  }
  return price.toLocaleString('ko-KR') + '원'
}

/* --------------------------------------------------------------------------
   아이템 카드 (오너 모드) - 04_my-shelf.html 기반
   -------------------------------------------------------------------------- */
interface OwnerItemCardProps {
  item: MyItemSummary
  onTogglePublish: (itemId: number, currentStatus: ItemStatus) => void
  onDelete: (itemId: number, title: string) => void
  isToggling: boolean
}

function OwnerItemCard({
  item,
  onTogglePublish,
  onDelete,
  isToggling,
}: OwnerItemCardProps) {
  const isPublished = item.status === 'PUBLISHED'
  const isDraft = item.status === 'DRAFT'

  return (
    <article
      className={`item-card item-card--owner ${isDraft ? 'item-card--draft' : ''}`}
      role="listitem"
      aria-label={`${item.title}${isDraft ? ' (비공개)' : ''}`}
    >
      {/* 오버레이 컨트롤 */}
      <div className="item-card-overlay" aria-label="상품 관리">
        <Link
          href={`/items/${item.itemId}/edit`}
          className="item-card-overlay__btn"
          aria-label={`${item.title} 수정`}
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
        </Link>
        <button
          className="item-card-overlay__btn item-card-overlay__btn--danger"
          aria-label={`${item.title} 삭제`}
          onClick={() => onDelete(item.itemId, item.title)}
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
            <path d="M10 11v6M14 11v6" />
            <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2" />
          </svg>
        </button>
      </div>

      {/* 카드 본문 */}
      <Link
        href={`/items/${item.itemId}`}
        className="item-card__link"
        aria-label={`${item.title} 상세보기`}
        tabIndex={-1}
      >
        <div className="item-card__thumb">
          {item.thumbnailUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={item.thumbnailUrl}
              alt={item.title}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <div
              className="item-card__thumb-placeholder"
              aria-hidden="true"
            >
              🖼
            </div>
          )}
          <div className="item-card__badge">
            <span className={`badge ${isDraft ? 'badge--neutral' : 'badge--success'}`}>
              {isDraft ? '비공개' : '공개'}
            </span>
          </div>
        </div>
        <div className="item-card__body">
          <h3 className="item-card__title">{item.title}</h3>
          <div className="item-card__footer">
            <span className="item-card__price">
              {item.price.toLocaleString('ko-KR')}원
            </span>
          </div>
        </div>
      </Link>

      {/* 공개/비공개 토글 */}
      <div
        className="publish-toggle"
        style={{ padding: '0 var(--space-4) var(--space-3)' }}
      >
        <label
          className="toggle-switch"
          aria-label={`${item.title} 공개 여부 전환`}
        >
          <input
            type="checkbox"
            checked={isPublished}
            disabled={isToggling}
            onChange={() => onTogglePublish(item.itemId, item.status)}
            aria-checked={isPublished}
          />
          <span className="toggle-switch__track" />
        </label>
        <span
          className="publish-toggle__label"
          style={{
            color: isDraft ? 'var(--color-text-disabled)' : undefined,
          }}
        >
          {isPublished ? '공개' : '비공개'}
        </span>
      </div>
    </article>
  )
}

/* --------------------------------------------------------------------------
   삭제 확인 모달
   -------------------------------------------------------------------------- */
function DeleteConfirmModal({
  title,
  onConfirm,
  onClose,
  isLoading,
}: {
  title: string
  onConfirm: () => void
  onClose: () => void
  isLoading: boolean
}) {
  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-modal-title"
    >
      <div className="modal">
        <div className="modal__header">
          <h2 className="modal__title" id="delete-modal-title">
            상품 삭제
          </h2>
          <button
            className="btn btn--ghost btn--icon"
            aria-label="모달 닫기"
            onClick={onClose}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="modal__body">
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-secondary)',
              lineHeight: 'var(--line-height-relaxed)',
            }}
          >
            <strong>&apos;{title}&apos;</strong> 상품을 삭제하시겠습니까?{' '}
            삭제된 상품은 복구할 수 없습니다.
          </p>
        </div>
        <div className="modal__footer">
          <Button variant="ghost" onClick={onClose}>
            취소
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={isLoading}>
            삭제
          </Button>
        </div>
      </div>
    </div>
  )
}

/* --------------------------------------------------------------------------
   메인 대시보드 페이지
   -------------------------------------------------------------------------- */
type StatusFilter = 'ALL' | 'PUBLISHED' | 'DRAFT'

const STATUS_FILTER_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'ALL', label: '전체' },
  { value: 'PUBLISHED', label: '공개' },
  { value: 'DRAFT', label: '비공개' },
]

export default function DashboardPage() {
  const toast = useToast()
  const { requireAuth, user } = useAuth()
  const queryClient = useQueryClient()

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [sort, setSort] = useState<'createdAt' | 'title' | 'price'>('createdAt')
  const [deleteTarget, setDeleteTarget] = useState<{
    itemId: number
    title: string
  } | null>(null)
  const [togglingId, setTogglingId] = useState<number | null>(null)

  // 인증 가드
  useEffect(() => {
    requireAuth('/dashboard')
  }, [requireAuth])

  const { data: stats, isLoading: statsLoading } = useSellerStats()

  const { data: myItems, isLoading: itemsLoading } = useMyItems({
    status: statusFilter === 'ALL' ? 'ALL' : statusFilter,
    sort,
    size: 50,
  })

  const deleteItem = useDeleteItem()

  /* 공개/비공개 토글 */
  const handleTogglePublish = async (
    itemId: number,
    currentStatus: ItemStatus
  ) => {
    const newStatus: ItemStatus =
      currentStatus === 'PUBLISHED' ? 'DRAFT' : 'PUBLISHED'
    setTogglingId(itemId)
    try {
      await updateItemStatus(itemId, newStatus)
      // 내 아이템 목록 캐시 무효화
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.myItems() })
      toast.success(
        newStatus === 'PUBLISHED' ? '상품을 공개했습니다.' : '상품을 비공개로 변경했습니다.'
      )
    } catch (e: any) {
      toast.error(e?.message ?? '상태 변경에 실패했습니다.')
    } finally {
      setTogglingId(null)
    }
  }

  /* 삭제 처리 */
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    try {
      await deleteItem.mutateAsync(deleteTarget.itemId)
      toast.success('상품이 삭제되었습니다.')
      setDeleteTarget(null)
    } catch (e: any) {
      toast.error(e?.message ?? '상품 삭제에 실패했습니다.')
    }
  }

  const items = myItems?.content ?? []
  const publishedCount = items.filter((i) => i.status === 'PUBLISHED').length
  const draftCount = items.filter((i) => i.status === 'DRAFT').length
  const totalCount = items.length

  return (
    <main className="page-body">
      {/* ── 프로필 히어로 영역 ─────────────────────────────────── */}
      <div className="profile-hero">
        <div className="profile-hero__inner">
          {/* 소유자 안내 배너 */}
          <div
            className="profile-owner-notice"
            role="note"
            aria-label="내 선반 관리 안내"
          >
            <span className="profile-owner-notice__text">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
                style={{ display: 'inline', verticalAlign: '-2px', marginRight: 4 }}
              >
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              현재 내 선반을 관리 중입니다. 비공개 상품도 함께 표시됩니다.
            </span>
            <div className="profile-owner-notice__actions">
              <Link href="/mypage" className="btn btn--ghost btn--sm">
                프로필 수정
              </Link>
              <Link href="/items/new" className="btn btn--primary btn--sm">
                + 상품 등록
              </Link>
            </div>
          </div>

          {/* 프로필 상단 */}
          <div className="profile-hero__top">
            <div className="profile-hero__avatar-wrap">
              <div
                className="profile-hero__avatar"
                aria-label={`${user?.nickname ?? ''} 프로필 이미지`}
              >
                {user?.profileImageUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={user.profileImageUrl}
                    alt={user.nickname}
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                      borderRadius: '50%',
                    }}
                  />
                ) : (
                  (user?.nickname ?? 'U')[0].toUpperCase()
                )}
              </div>
            </div>

            <div className="profile-hero__info">
              <h1 className="profile-hero__nickname">
                {user?.nickname ?? '...'}
              </h1>
              <div
                className="profile-hero__stats"
                role="list"
                aria-label="셀러 통계"
              >
                <div className="profile-hero__stat" role="listitem">
                  <span className="profile-hero__stat-value">{totalCount}</span>
                  <span className="profile-hero__stat-label">전체 상품</span>
                </div>
                <div
                  className="profile-hero__stat-divider"
                  aria-hidden="true"
                />
                <div className="profile-hero__stat" role="listitem">
                  <span className="profile-hero__stat-value">
                    {publishedCount}
                  </span>
                  <span className="profile-hero__stat-label">공개 상품</span>
                </div>
                <div
                  className="profile-hero__stat-divider"
                  aria-hidden="true"
                />
                <div className="profile-hero__stat" role="listitem">
                  <span className="profile-hero__stat-value">
                    {statsLoading
                      ? '...'
                      : (stats?.activeSubscribers ?? 0).toLocaleString('ko-KR')}
                  </span>
                  <span className="profile-hero__stat-label">구독자</span>
                </div>
              </div>
            </div>
          </div>

          {/* 탭 네비게이션 */}
          <nav
            className="profile-tabs"
            role="tablist"
            aria-label="대시보드 탭"
          >
            <button
              className="profile-tab profile-tab--active"
              role="tab"
              aria-selected="true"
            >
              내 선반
            </button>
            <Link href="/dashboard/revenue" className="profile-tab" role="tab">
              수익 현황
            </Link>
            <Link href="/mypage?tab=orders" className="profile-tab" role="tab">
              구매 내역
            </Link>
            <Link href="/mypage?tab=subscriptions" className="profile-tab" role="tab">
              구독 내역
            </Link>
          </nav>
        </div>
      </div>

      {/* ── 통계 카드 영역 ─────────────────────────────────────── */}
      <div
        style={{
          maxWidth: 'var(--container-xl)',
          marginInline: 'auto',
          paddingInline: 'var(--container-padding)',
          paddingTop: 'var(--space-8)',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 'var(--space-4)',
            marginBottom: 'var(--space-8)',
          }}
          role="list"
          aria-label="주요 통계"
        >
          <div role="listitem">
            <StatCard
              label="총 판매액"
              value={
                statsLoading
                  ? '...'
                  : formatPrice(stats?.totalRevenue ?? 0)
              }
              color="var(--color-primary)"
              icon={
                <svg
                  width="22"
                  height="22"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <line x1="12" y1="1" x2="12" y2="23" />
                  <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
                </svg>
              }
            />
          </div>
          <div role="listitem">
            <StatCard
              label="총 주문 수"
              value={
                statsLoading
                  ? '...'
                  : `${(stats?.totalOrders ?? 0).toLocaleString('ko-KR')}건`
              }
              color="var(--color-info)"
              icon={
                <svg
                  width="22"
                  height="22"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <path d="M16 10a4 4 0 01-8 0" />
                </svg>
              }
            />
          </div>
          <div role="listitem">
            <StatCard
              label="활성 구독자 수"
              value={
                statsLoading
                  ? '...'
                  : `${(stats?.activeSubscribers ?? 0).toLocaleString('ko-KR')}명`
              }
              color="var(--color-success)"
              icon={
                <svg
                  width="22"
                  height="22"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 00-3-3.87" />
                  <path d="M16 3.13a4 4 0 010 7.75" />
                </svg>
              }
            />
          </div>
        </div>

        {/* ── 아이템 목록 영역 ───────────────────────────────────── */}
        <div className="shelf-layout" style={{ paddingTop: 0, paddingInline: 0 }}>
          {/* 툴바 */}
          <div className="shelf-owner-toolbar" aria-label="선반 관리 도구">
            <div
              className="status-tab-group"
              role="group"
              aria-label="상태 필터"
            >
              {STATUS_FILTER_OPTIONS.map((opt) => {
                const count =
                  opt.value === 'ALL'
                    ? totalCount
                    : opt.value === 'PUBLISHED'
                      ? publishedCount
                      : draftCount
                return (
                  <button
                    key={opt.value}
                    className={`status-tab ${statusFilter === opt.value ? 'status-tab--active' : ''}`}
                    aria-pressed={statusFilter === opt.value}
                    onClick={() => setStatusFilter(opt.value)}
                  >
                    {opt.label} ({count})
                  </button>
                )
              })}
            </div>

            <div className="shelf-owner-toolbar__actions">
              <label htmlFor="shelf-sort" className="sr-only">
                정렬 기준
              </label>
              <select
                id="shelf-sort"
                className="sort-select"
                value={sort}
                onChange={(e) =>
                  setSort(e.target.value as typeof sort)
                }
                aria-label="정렬 기준"
              >
                <option value="createdAt">최신 등록순</option>
                <option value="title">이름순</option>
                <option value="price">가격순</option>
              </select>
              <Link href="/items/new" className="btn btn--primary btn--sm">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  aria-hidden="true"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                새 상품 등록
              </Link>
            </div>
          </div>

          {/* 아이템 그리드 */}
          {itemsLoading ? (
            <div
              className="shelf-grid"
              aria-label="상품 목록 로딩 중"
              aria-busy="true"
            >
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="item-card" aria-hidden="true">
                  <div className="item-card__thumb skeleton" />
                  <div className="item-card__body">
                    <div
                      className="skeleton skeleton--text"
                      style={{ height: '0.875rem', marginBottom: 'var(--space-2)' }}
                    />
                    <div
                      className="skeleton skeleton--text"
                      style={{ width: '60%', height: '0.875rem' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : items.length === 0 ? (
            <div className="shelf-grid">
              <div className="shelf-empty">
                <div className="shelf-empty__icon" aria-hidden="true">
                  📦
                </div>
                <h2 className="shelf-empty__title">상품이 없습니다</h2>
                <p className="shelf-empty__desc">
                  첫 번째 상품을 등록하고 선반을 채워보세요!
                </p>
                <Link href="/items/new" className="btn btn--primary">
                  + 첫 상품 등록하기
                </Link>
              </div>
            </div>
          ) : (
            <div
              className="shelf-grid"
              role="list"
              aria-label="내 상품 목록"
            >
              {items.map((item) => (
                <OwnerItemCard
                  key={item.itemId}
                  item={item}
                  onTogglePublish={handleTogglePublish}
                  onDelete={(id, title) => setDeleteTarget({ itemId: id, title })}
                  isToggling={togglingId === item.itemId}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 삭제 확인 모달 */}
      {deleteTarget && (
        <DeleteConfirmModal
          title={deleteTarget.title}
          onConfirm={handleDeleteConfirm}
          onClose={() => setDeleteTarget(null)}
          isLoading={deleteItem.isPending}
        />
      )}
    </main>
  )
}
