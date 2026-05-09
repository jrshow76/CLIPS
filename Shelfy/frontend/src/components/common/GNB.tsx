/**
 * GNB (Global Navigation Bar) 공통 컴포넌트
 * Designer common.css 구조 기반: .gnb > .gnb__inner > .gnb__logo + .gnb__search + .gnb__nav
 *
 * 로그인/비로그인 분기:
 * - 비로그인: 탐색, 로그인, 회원가입 버튼
 * - 로그인: 탐색, 내 선반, 아바타 메뉴
 */

'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'

export function GNB() {
  const { isLoggedIn, user, logout } = useAuth()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = searchQuery.trim()
    if (trimmed) {
      router.push(`/browse?q=${encodeURIComponent(trimmed)}`)
    }
  }

  async function handleLogout() {
    setIsMenuOpen(false)
    await logout()
  }

  return (
    <header className="gnb" role="banner">
      <div className="gnb__inner">
        {/* 로고 */}
        <Link href="/" className="gnb__logo" aria-label="Shelfy 홈">
          <div className="gnb__logo-mark" aria-hidden="true">
            S
          </div>
          <span className="gnb__logo-text">Shelfy</span>
        </Link>

        {/* 검색 인풋 */}
        <form
          className="gnb__search"
          onSubmit={handleSearchSubmit}
          role="search"
          aria-label="상품 검색"
        >
          <svg
            className="gnb__search-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            type="search"
            className="gnb__search-input"
            placeholder="상품, 셀러 검색..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="검색어 입력"
          />
        </form>

        {/* 네비게이션 영역 */}
        <nav className="gnb__nav" aria-label="주요 메뉴">
          <Link href="/browse" className="gnb__nav-item">
            탐색
          </Link>

          {isLoggedIn ? (
            <>
              <Link
                href={`/shelf/${user?.userId}`}
                className="gnb__nav-item"
              >
                내 선반
              </Link>

              {/* 아바타 드롭다운 */}
              <div style={{ position: 'relative' }} ref={menuRef}>
                <button
                  className="gnb__avatar"
                  onClick={() => setIsMenuOpen((prev) => !prev)}
                  aria-expanded={isMenuOpen}
                  aria-haspopup="true"
                  aria-label={`${user?.nickname ?? '사용자'} 메뉴`}
                >
                  {user?.profileImageUrl ? (
                    <Image
                      src={user.profileImageUrl}
                      alt={user.nickname}
                      width={36}
                      height={36}
                      style={{ objectFit: 'cover' }}
                    />
                  ) : (
                    <span
                      style={{
                        width: '100%',
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: 'var(--font-weight-semibold)',
                        color: 'var(--color-text-secondary)',
                      }}
                      aria-hidden="true"
                    >
                      {user?.nickname?.[0]?.toUpperCase() ?? 'U'}
                    </span>
                  )}
                </button>

                {isMenuOpen && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 'calc(100% + var(--space-2))',
                      right: 0,
                      minWidth: 160,
                      backgroundColor: 'var(--color-bg-surface)',
                      border: '1px solid var(--color-border-default)',
                      borderRadius: 'var(--radius-lg)',
                      boxShadow: 'var(--shadow-md)',
                      zIndex: 'var(--z-dropdown)',
                      overflow: 'hidden',
                    }}
                    role="menu"
                  >
                    <Link
                      href="/shelf/me"
                      className="gnb__nav-item"
                      style={{ display: 'flex', width: '100%', borderRadius: 0 }}
                      onClick={() => setIsMenuOpen(false)}
                      role="menuitem"
                    >
                      내 선반
                    </Link>
                    <Link
                      href="/shelf/me/settings"
                      className="gnb__nav-item"
                      style={{ display: 'flex', width: '100%', borderRadius: 0 }}
                      onClick={() => setIsMenuOpen(false)}
                      role="menuitem"
                    >
                      설정
                    </Link>
                    <button
                      className="gnb__nav-item"
                      style={{
                        width: '100%',
                        border: 'none',
                        background: 'none',
                        textAlign: 'left',
                        borderTop: '1px solid var(--color-border-default)',
                        borderRadius: 0,
                        color: 'var(--color-error)',
                      }}
                      onClick={handleLogout}
                      role="menuitem"
                    >
                      로그아웃
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <Link href="/login" className="btn btn--ghost btn--sm">
                로그인
              </Link>
              <Link href="/signup" className="btn btn--primary btn--sm">
                시작하기
              </Link>
            </>
          )}
        </nav>

        {/* 모바일 메뉴 버튼 */}
        <button
          className="gnb__mobile-menu-btn"
          aria-label="모바일 메뉴 열기"
          aria-expanded={false}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>
    </header>
  )
}
