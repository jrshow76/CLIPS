/**
 * ItemCard 공통 컴포넌트
 * Designer common.css 구조 기반:
 * .item-card > .item-card__thumb + .item-card__body
 * .item-card__body > .item-card__seller + .item-card__title + .item-card__footer
 */

import Link from 'next/link'
import Image from 'next/image'
import { SaleTypeBadge } from './Badge'
import type { ItemSummary } from '@/types/item'

interface ItemCardProps {
  item: ItemSummary
  className?: string
}

/** 가격 포맷 (한국 원화) */
function formatPrice(price: number): string {
  return price.toLocaleString('ko-KR') + '원'
}

export function ItemCard({ item, className = '' }: ItemCardProps) {
  return (
    <Link
      href={`/items/${item.itemId}`}
      className={`item-card ${className}`.trim()}
      aria-label={`${item.title} - ${formatPrice(item.price)}`}
    >
      {/* 썸네일 영역 */}
      <div className="item-card__thumb">
        {item.thumbnailUrl ? (
          <Image
            src={item.thumbnailUrl}
            alt={item.title}
            fill
            sizes="(max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
            style={{ objectFit: 'cover' }}
          />
        ) : (
          <div className="item-card__thumb-placeholder" aria-hidden="true">
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <path d="M21 15l-5-5L5 21" />
            </svg>
          </div>
        )}

        {/* 판매 유형 배지 */}
        <div className="item-card__badge">
          <SaleTypeBadge saleType={item.saleType} />
        </div>
      </div>

      {/* 카드 본문 */}
      <div className="item-card__body">
        {/* 셀러 정보 */}
        <div className="item-card__seller">
          <div className="item-card__seller-avatar" aria-hidden="true">
            {item.seller.profileImageUrl ? (
              <Image
                src={item.seller.profileImageUrl}
                alt={item.seller.nickname}
                width={22}
                height={22}
                style={{ objectFit: 'cover', borderRadius: '50%' }}
              />
            ) : null}
          </div>
          <span className="item-card__seller-name">{item.seller.nickname}</span>
        </div>

        {/* 상품명 (2줄 클램프) */}
        <h3 className="item-card__title">{item.title}</h3>

        {/* 푸터: 가격 */}
        <div className="item-card__footer">
          <div className="item-card__price">
            {item.saleType === 'SUBSCRIBE' ? (
              <>
                <span className="item-card__price-from">월</span>{' '}
                {formatPrice(item.price)}
              </>
            ) : (
              formatPrice(item.price)
            )}
          </div>
        </div>
      </div>
    </Link>
  )
}

/** 스켈레톤 카드 (로딩 상태) */
export function ItemCardSkeleton() {
  return (
    <div className="item-card" aria-hidden="true">
      <div className="item-card__thumb skeleton" />
      <div className="item-card__body">
        <div
          className="item-card__seller"
          style={{ marginBottom: 'var(--space-2)' }}
        >
          <div
            className="skeleton"
            style={{ width: 22, height: 22, borderRadius: '50%' }}
          />
          <div
            className="skeleton skeleton--text"
            style={{ width: 60, height: '0.75rem' }}
          />
        </div>
        <div
          className="skeleton skeleton--text"
          style={{ height: '0.875rem', marginBottom: 'var(--space-2)' }}
        />
        <div
          className="skeleton skeleton--text"
          style={{ width: '60%', height: '0.875rem', marginBottom: 'var(--space-3)' }}
        />
        <div
          className="skeleton skeleton--text"
          style={{ width: '40%', height: '1rem' }}
        />
      </div>
    </div>
  )
}
