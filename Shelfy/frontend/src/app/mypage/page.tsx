'use client'

/**
 * SCR-025 마이페이지 (CSR)
 * 탭: 내 정보 수정 | 주문 내역 | 구독 내역
 */

import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { ProfileForm } from './components/ProfileForm'
import { OrderList } from './components/OrderList'
import { SubscriptionList } from './components/SubscriptionList'

type TabId = 'profile' | 'orders' | 'subscriptions'

const TABS: { id: TabId; label: string }[] = [
  { id: 'profile', label: '내 정보 수정' },
  { id: 'orders', label: '주문 내역' },
  { id: 'subscriptions', label: '구독 내역' },
]

export default function MyPage() {
  const { requireAuth } = useAuth()
  const [activeTab, setActiveTab] = useState<TabId>('profile')

  // 인증 가드
  useEffect(() => {
    requireAuth('/mypage')
  }, [requireAuth])

  return (
    <main className="page-body">
      <div
        style={{
          maxWidth: 'var(--container-md)',
          marginInline: 'auto',
          paddingInline: 'var(--container-padding)',
          paddingTop: 'var(--space-10)',
          paddingBottom: 'var(--space-20)',
        }}
      >
        {/* 페이지 헤더 */}
        <div style={{ marginBottom: 'var(--space-8)' }}>
          <h1
            style={{
              fontSize: 'var(--font-size-3xl)',
              fontWeight: 'var(--font-weight-extrabold)',
              color: 'var(--color-text-primary)',
              letterSpacing: 'var(--letter-spacing-tight)',
              marginBottom: 'var(--space-2)',
            }}
          >
            마이페이지
          </h1>
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-tertiary)',
            }}
          >
            내 정보를 관리하고 주문 및 구독 내역을 확인하세요.
          </p>
        </div>

        {/* 탭 네비게이션 */}
        <nav
          role="tablist"
          aria-label="마이페이지 탭"
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--color-border-default)',
            marginBottom: 'var(--space-8)',
          }}
        >
          {TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={activeTab === tab.id}
              aria-controls={`tabpanel-${tab.id}`}
              className={`profile-tab ${activeTab === tab.id ? 'profile-tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* 탭 패널 */}
        <div
          id={`tabpanel-profile`}
          role="tabpanel"
          aria-labelledby="tab-profile"
          hidden={activeTab !== 'profile'}
        >
          {activeTab === 'profile' && (
            <div
              style={{
                background: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-default)',
                borderRadius: 'var(--radius-2xl)',
                padding: 'var(--space-8)',
              }}
            >
              <ProfileForm />
            </div>
          )}
        </div>

        <div
          id={`tabpanel-orders`}
          role="tabpanel"
          aria-labelledby="tab-orders"
          hidden={activeTab !== 'orders'}
        >
          {activeTab === 'orders' && <OrderList />}
        </div>

        <div
          id={`tabpanel-subscriptions`}
          role="tabpanel"
          aria-labelledby="tab-subscriptions"
          hidden={activeTab !== 'subscriptions'}
        >
          {activeTab === 'subscriptions' && <SubscriptionList />}
        </div>
      </div>
    </main>
  )
}
