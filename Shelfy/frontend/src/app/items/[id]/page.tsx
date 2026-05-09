/**
 * 아이템 상세 페이지 (SCR-003)
 * 렌더링 전략: SSR (서버에서 상품 상세 데이터 fetch)
 * - generateMetadata로 동적 OG 태그 생성
 * - 구매/구독 버튼은 클라이언트 컴포넌트로 분리
 */

import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { SaleTypeBadge } from '@/components/common/Badge'
import { ItemPurchasePanel } from './ItemPurchasePanel'
import type { ItemDetail } from '@/types/item'
import type { ApiResponse } from '@/types/api'

interface ItemDetailPageProps {
  params: { id: string }
}

async function fetchItem(itemId: string): Promise<ItemDetail | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  if (!apiUrl) return null

  try {
    const res = await fetch(`${apiUrl}/items/${itemId}`, {
      cache: 'no-store', // SSR: 항상 최신 데이터
    })
    if (res.status === 404 || res.status === 403) return null
    if (!res.ok) return null

    const json: ApiResponse<ItemDetail> = await res.json()
    return json.success && json.data ? json.data : null
  } catch {
    return null
  }
}

export async function generateMetadata({
  params,
}: ItemDetailPageProps): Promise<Metadata> {
  const item = await fetchItem(params.id)
  if (!item) return { title: '상품을 찾을 수 없습니다' }

  return {
    title: item.title,
    description: item.description.slice(0, 160),
    openGraph: {
      title: item.title,
      description: item.description.slice(0, 160),
      images: item.images.find((img) => img.isThumbnail)?.url
        ? [{ url: item.images.find((img) => img.isThumbnail)!.url }]
        : [],
    },
  }
}

function formatPrice(price: number): string {
  return price.toLocaleString('ko-KR') + '원'
}

export default async function ItemDetailPage({ params }: ItemDetailPageProps) {
  const item = await fetchItem(params.id)

  if (!item) {
    notFound()
  }

  const thumbnailImage = item.images.find((img) => img.isThumbnail) ?? item.images[0]
  const otherImages = item.images.filter((img) => !img.isThumbnail)

  return (
    <main className="page-body">
      <div className="container" style={{ paddingTop: 'var(--space-8)', paddingBottom: 'var(--space-20)' }}>
        {/* 브레드크럼 */}
        <nav
          className="breadcrumb"
          aria-label="탐색 경로"
          style={{
            display: 'flex',
            gap: 'var(--space-2)',
            alignItems: 'center',
            marginBottom: 'var(--space-6)',
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-tertiary)',
          }}
        >
          <Link href="/" style={{ color: 'var(--color-text-tertiary)' }}>홈</Link>
          <span aria-hidden="true">/</span>
          <Link href="/browse" style={{ color: 'var(--color-text-tertiary)' }}>탐색</Link>
          <span aria-hidden="true">/</span>
          <span
            aria-current="page"
            style={{ color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 300 }}
          >
            {item.title}
          </span>
        </nav>

        {/* 2컬럼 레이아웃 */}
        <div
          className="detail-layout"
          style={{ display: 'flex', gap: 'var(--space-12)', alignItems: 'flex-start' }}
        >
          {/* 콘텐츠 영역 */}
          <div className="detail-body" style={{ flex: 1, minWidth: 0 }}>
            {/* 이미지 갤러리 */}
            <section className="gallery" aria-label="상품 이미지">
              {thumbnailImage && (
                <div
                  style={{
                    position: 'relative',
                    width: '100%',
                    paddingTop: '66.67%',
                    borderRadius: 'var(--radius-xl)',
                    overflow: 'hidden',
                    background: 'var(--color-bg-muted)',
                    marginBottom: 'var(--space-3)',
                  }}
                >
                  <Image
                    src={thumbnailImage.url}
                    alt={`${item.title} 대표 이미지`}
                    fill
                    priority
                    sizes="(max-width: 1024px) 100vw, 65vw"
                    style={{ objectFit: 'cover' }}
                  />
                </div>
              )}
              {otherImages.length > 0 && (
                <div
                  style={{ display: 'flex', gap: 'var(--space-2)', overflowX: 'auto' }}
                  role="list"
                  aria-label="추가 이미지"
                >
                  {otherImages.map((img, idx) => (
                    <div
                      key={img.imageId}
                      style={{
                        position: 'relative',
                        width: 80,
                        height: 80,
                        flexShrink: 0,
                        borderRadius: 'var(--radius-lg)',
                        overflow: 'hidden',
                        background: 'var(--color-bg-muted)',
                        border: '1px solid var(--color-border-default)',
                      }}
                      role="listitem"
                    >
                      <Image
                        src={img.url}
                        alt={`${item.title} 이미지 ${idx + 2}`}
                        fill
                        sizes="80px"
                        style={{ objectFit: 'cover' }}
                      />
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* 상품 설명 */}
            <section
              className="detail-section"
              aria-label="상품 설명"
              style={{ marginTop: 'var(--space-10)' }}
            >
              <h1
                style={{
                  fontSize: 'var(--font-size-3xl)',
                  fontWeight: 'var(--font-weight-bold)',
                  marginBottom: 'var(--space-4)',
                }}
              >
                {item.title}
              </h1>

              <div
                style={{
                  display: 'flex',
                  gap: 'var(--space-2)',
                  flexWrap: 'wrap',
                  marginBottom: 'var(--space-6)',
                  alignItems: 'center',
                }}
              >
                <SaleTypeBadge saleType={item.saleType} />
                <span
                  className="badge badge--neutral"
                  style={{ textTransform: 'none' }}
                >
                  {item.category}
                </span>
                <span
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-text-tertiary)',
                  }}
                >
                  조회 {item.viewCount.toLocaleString()}회
                </span>
              </div>

              <p
                style={{
                  fontSize: 'var(--font-size-base)',
                  lineHeight: 'var(--line-height-relaxed)',
                  color: 'var(--color-text-secondary)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {item.description}
              </p>

              {/* 태그 */}
              {item.tags.length > 0 && (
                <div
                  style={{
                    display: 'flex',
                    gap: 'var(--space-2)',
                    flexWrap: 'wrap',
                    marginTop: 'var(--space-6)',
                  }}
                >
                  {item.tags.map((tag) => (
                    <Link
                      key={tag}
                      href={`/browse?q=${encodeURIComponent(tag)}`}
                      className="tag"
                    >
                      #{tag}
                    </Link>
                  ))}
                </div>
              )}
            </section>

            {/* 셀러 정보 */}
            <section
              className="detail-section"
              aria-label="판매자 정보"
              style={{
                marginTop: 'var(--space-10)',
                padding: 'var(--space-6)',
                background: 'var(--color-bg-muted)',
                borderRadius: 'var(--radius-xl)',
              }}
            >
              <h2
                style={{
                  fontSize: 'var(--font-size-base)',
                  fontWeight: 'var(--font-weight-semibold)',
                  marginBottom: 'var(--space-4)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                판매자 정보
              </h2>
              <Link
                href={`/shelf/${item.seller.userId}`}
                style={{
                  display: 'flex',
                  gap: 'var(--space-4)',
                  alignItems: 'center',
                  textDecoration: 'none',
                }}
              >
                <div className="avatar avatar--lg">
                  {item.seller.profileImageUrl ? (
                    <Image
                      src={item.seller.profileImageUrl}
                      alt={item.seller.nickname}
                      width={64}
                      height={64}
                      style={{ objectFit: 'cover' }}
                    />
                  ) : (
                    <span aria-hidden="true">
                      {item.seller.nickname[0]?.toUpperCase()}
                    </span>
                  )}
                </div>
                <div>
                  <p
                    style={{
                      fontSize: 'var(--font-size-base)',
                      fontWeight: 'var(--font-weight-semibold)',
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    {item.seller.nickname}
                  </p>
                  <p
                    style={{
                      fontSize: 'var(--font-size-sm)',
                      color: 'var(--color-text-tertiary)',
                    }}
                  >
                    상품 {item.seller.itemCount}개
                  </p>
                </div>
              </Link>
            </section>
          </div>

          {/* 구매 패널 (스티키, 클라이언트 컴포넌트) */}
          <aside
            className="item-panel"
            style={{
              width: 360,
              flexShrink: 0,
              position: 'sticky',
              top: 'calc(var(--gnb-height) + var(--space-6))',
            }}
          >
            <ItemPurchasePanel item={item} />
          </aside>
        </div>
      </div>
    </main>
  )
}
