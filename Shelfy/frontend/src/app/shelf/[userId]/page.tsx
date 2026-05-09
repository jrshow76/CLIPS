/**
 * 마이 선반 / 셀러 프로필 페이지 (SCR-004 / SCR-021)
 * 렌더링 전략: SSR (서버에서 셀러 프로필 fetch)
 * - userId 파라미터: 숫자 ID (추후 nickname 기반으로 확장 가능)
 */

import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { ItemCard } from '@/components/common/ItemCard'
import type { SellerProfile } from '@/types/user'
import type { ApiResponse } from '@/types/api'

interface ShelfPageProps {
  params: { userId: string }
  searchParams: { tab?: string }
}

async function fetchSellerProfile(userId: string): Promise<SellerProfile | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  if (!apiUrl) return null

  try {
    // userId가 숫자인 경우 nickname을 알 수 없으므로
    // 실제로는 userId로 nickname을 먼저 조회하거나 백엔드가 양쪽 모두 지원해야 함.
    // 여기서는 userId를 nickname처럼 사용하는 임시 구현.
    const res = await fetch(`${apiUrl}/users/${userId}/profile`, {
      cache: 'no-store',
    })
    if (res.status === 404) return null
    if (!res.ok) return null

    const json: ApiResponse<SellerProfile> = await res.json()
    return json.success && json.data ? json.data : null
  } catch {
    return null
  }
}

export async function generateMetadata({
  params,
}: ShelfPageProps): Promise<Metadata> {
  const profile = await fetchSellerProfile(params.userId)
  if (!profile) return { title: '선반을 찾을 수 없습니다' }

  return {
    title: `${profile.nickname}의 선반`,
    description: profile.bio ?? `${profile.nickname}의 디지털 콘텐츠 선반`,
    openGraph: {
      title: `${profile.nickname}의 선반`,
      images: profile.profileImageUrl ? [{ url: profile.profileImageUrl }] : [],
    },
  }
}

function formatJoinDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
  })
}

export default async function ShelfPage({ params, searchParams }: ShelfPageProps) {
  const profile = await fetchSellerProfile(params.userId)

  if (!profile) {
    notFound()
  }

  const activeTab = searchParams.tab ?? 'items'
  const items = profile.items.content

  return (
    <main className="page-body">
      {/* 프로필 히어로 */}
      <div
        className="profile-hero"
        style={{
          background: 'var(--color-bg-surface)',
          borderBottom: '1px solid var(--color-border-default)',
          padding: 'var(--space-10) 0 0',
        }}
      >
        <div className="container">
          {/* 프로필 상단: 아바타 + 이름 + 통계 */}
          <div
            className="profile-hero__top"
            style={{
              display: 'flex',
              gap: 'var(--space-6)',
              alignItems: 'flex-start',
              marginBottom: 'var(--space-8)',
            }}
          >
            {/* 아바타 */}
            <div className="avatar avatar--2xl" style={{ flexShrink: 0 }}>
              {profile.profileImageUrl ? (
                <Image
                  src={profile.profileImageUrl}
                  alt={`${profile.nickname} 프로필 이미지`}
                  width={96}
                  height={96}
                  style={{ objectFit: 'cover' }}
                />
              ) : (
                <span style={{ fontSize: 'var(--font-size-3xl)' }} aria-hidden="true">
                  {profile.nickname[0]?.toUpperCase()}
                </span>
              )}
            </div>

            {/* 이름 + 소개 + 통계 */}
            <div style={{ flex: 1 }}>
              <h1
                style={{
                  fontSize: 'var(--font-size-2xl)',
                  fontWeight: 'var(--font-weight-bold)',
                  marginBottom: 'var(--space-2)',
                }}
              >
                {profile.nickname}
              </h1>
              {profile.bio && (
                <p
                  style={{
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--color-text-secondary)',
                    lineHeight: 'var(--line-height-relaxed)',
                    marginBottom: 'var(--space-4)',
                    maxWidth: 480,
                  }}
                >
                  {profile.bio}
                </p>
              )}
              {/* 통계 */}
              <div
                style={{
                  display: 'flex',
                  gap: 'var(--space-6)',
                  fontSize: 'var(--font-size-sm)',
                }}
              >
                <div>
                  <strong style={{ color: 'var(--color-text-primary)' }}>
                    {profile.itemCount}
                  </strong>
                  <span style={{ color: 'var(--color-text-tertiary)', marginLeft: 'var(--space-1)' }}>
                    상품
                  </span>
                </div>
                <div>
                  <strong style={{ color: 'var(--color-text-primary)' }}>
                    {profile.subscriberCount}
                  </strong>
                  <span style={{ color: 'var(--color-text-tertiary)', marginLeft: 'var(--space-1)' }}>
                    구독자
                  </span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>
                    {formatJoinDate(profile.joinedAt)} 가입
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* 탭 네비게이션 */}
          <nav
            className="profile-tabs"
            aria-label="프로필 탭"
            style={{
              display: 'flex',
              borderBottom: 'none',
            }}
          >
            {[
              { value: 'items', label: '상품' },
            ].map((tab) => (
              <Link
                key={tab.value}
                href={`/shelf/${params.userId}?tab=${tab.value}`}
                style={{
                  padding: 'var(--space-3) var(--space-6)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color:
                    activeTab === tab.value
                      ? 'var(--color-primary)'
                      : 'var(--color-text-tertiary)',
                  borderBottom:
                    activeTab === tab.value
                      ? '2px solid var(--color-primary)'
                      : '2px solid transparent',
                  textDecoration: 'none',
                  transition: 'color var(--transition-base)',
                }}
                aria-current={activeTab === tab.value ? 'page' : undefined}
              >
                {tab.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* 선반 콘텐츠 */}
      <div className="shelf-layout">
        <div
          className="container"
          style={{
            paddingTop: 'var(--space-8)',
            paddingBottom: 'var(--space-20)',
          }}
        >
          {items.length > 0 ? (
            <div className="shelf-grid grid grid--4">
              {items.map((item) => (
                <ItemCard key={item.itemId} item={item} />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state__icon" aria-hidden="true">
                <svg
                  width="48"
                  height="48"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                  <polyline points="9 22 9 12 15 12 15 22" />
                </svg>
              </div>
              <p className="empty-state__title">아직 상품이 없어요</p>
              <p className="empty-state__desc">
                {profile.nickname}님이 아직 상품을 등록하지 않았습니다.
              </p>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
