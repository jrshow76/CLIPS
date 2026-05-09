/**
 * 메인 랜딩 페이지 (SCR-001)
 * 렌더링 전략: ISR (revalidate: 60초)
 * - 초기 아이템 목록을 서버에서 fetch하여 HTML에 포함
 * - 이후 클라이언트에서 TanStack Query로 stale 시 재조회
 */

import type { Metadata } from 'next'
import Link from 'next/link'
import { ItemCard } from '@/components/common/ItemCard'
import type { ItemSummary } from '@/types/item'
import type { ApiResponse, PageResponse } from '@/types/api'

export const metadata: Metadata = {
  title: 'Shelfy - 당신의 선반을 세상에 공개하세요',
}

// ISR: 60초마다 재생성
export const revalidate = 60

async function fetchFeaturedItems(): Promise<ItemSummary[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  if (!apiUrl) return []

  try {
    const res = await fetch(`${apiUrl}/items?sort=popular&size=8`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) return []

    const json: ApiResponse<PageResponse<ItemSummary>> = await res.json()
    return json.success && json.data ? json.data.content : []
  } catch {
    return []
  }
}

async function fetchLatestItems(): Promise<ItemSummary[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  if (!apiUrl) return []

  try {
    const res = await fetch(`${apiUrl}/items?sort=latest&size=8`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) return []

    const json: ApiResponse<PageResponse<ItemSummary>> = await res.json()
    return json.success && json.data ? json.data.content : []
  } catch {
    return []
  }
}

export default async function HomePage() {
  const [featuredItems, latestItems] = await Promise.all([
    fetchFeaturedItems(),
    fetchLatestItems(),
  ])

  return (
    <main className="page-body">
      {/* 히어로 섹션 */}
      <section className="hero" style={{ padding: 'var(--space-24) 0', background: 'var(--color-bg-base)' }}>
        <div className="container" style={{ textAlign: 'center' }}>
          <h1
            style={{
              fontSize: 'var(--font-size-5xl)',
              fontWeight: 'var(--font-weight-extrabold)',
              letterSpacing: 'var(--letter-spacing-tight)',
              lineHeight: 'var(--line-height-tight)',
              color: 'var(--color-text-primary)',
              marginBottom: 'var(--space-6)',
            }}
          >
            당신의 선반을
            <br />
            <span style={{ color: 'var(--color-primary)' }}>세상에 공개하세요</span>
          </h1>
          <p
            style={{
              fontSize: 'var(--font-size-lg)',
              color: 'var(--color-text-secondary)',
              lineHeight: 'var(--line-height-relaxed)',
              maxWidth: 520,
              margin: '0 auto var(--space-10)',
            }}
          >
            디지털 콘텐츠를 선반에 진열하고, 전 세계 사용자가 구매하거나 구독할 수 있는 나만의 공간을 만들어보세요.
          </p>
          <div
            style={{
              display: 'flex',
              gap: 'var(--space-4)',
              justifyContent: 'center',
              flexWrap: 'wrap',
            }}
          >
            <Link href="/signup" className="btn btn--primary btn--xl">
              선반 만들기
            </Link>
            <Link href="/browse" className="btn btn--secondary btn--xl">
              둘러보기
            </Link>
          </div>
        </div>
      </section>

      {/* 인기 상품 섹션 */}
      {featuredItems.length > 0 && (
        <section style={{ padding: 'var(--space-16) 0' }}>
          <div className="container">
            <div className="section-header">
              <div>
                <h2 className="section-title">인기 상품</h2>
                <p className="section-subtitle">지금 가장 많이 찾는 콘텐츠</p>
              </div>
              <Link href="/browse?sort=popular" className="section-link">
                전체 보기
              </Link>
            </div>
            <div className="grid grid--4">
              {featuredItems.map((item) => (
                <ItemCard key={item.itemId} item={item} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* 최신 상품 섹션 */}
      {latestItems.length > 0 && (
        <section
          style={{
            padding: 'var(--space-16) 0',
            background: 'var(--color-bg-muted)',
          }}
        >
          <div className="container">
            <div className="section-header">
              <div>
                <h2 className="section-title">새로 올라왔어요</h2>
                <p className="section-subtitle">최근 등록된 신규 콘텐츠</p>
              </div>
              <Link href="/browse?sort=latest" className="section-link">
                전체 보기
              </Link>
            </div>
            <div className="grid grid--4">
              {latestItems.map((item) => (
                <ItemCard key={item.itemId} item={item} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* CTA 배너 */}
      <section
        style={{
          background: 'var(--color-primary)',
          padding: 'var(--space-16) 0',
          textAlign: 'center',
        }}
      >
        <div className="container">
          <h2
            style={{
              fontSize: 'var(--font-size-3xl)',
              fontWeight: 'var(--font-weight-bold)',
              color: 'var(--color-text-inverse)',
              marginBottom: 'var(--space-4)',
            }}
          >
            지금 바로 시작하세요
          </h2>
          <p
            style={{
              color: 'rgba(255,255,255,0.85)',
              fontSize: 'var(--font-size-base)',
              marginBottom: 'var(--space-8)',
            }}
          >
            나만의 디지털 선반을 만들고 수익을 창출해보세요.
          </p>
          <Link
            href="/signup"
            className="btn btn--xl"
            style={{
              backgroundColor: 'var(--color-text-inverse)',
              color: 'var(--color-primary)',
              borderColor: 'transparent',
            }}
          >
            무료로 시작하기
          </Link>
        </div>
      </section>
    </main>
  )
}
