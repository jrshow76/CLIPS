/**
 * Skeleton 공통 컴포넌트
 * Designer common.css 기반: .skeleton, .skeleton--text
 */

import React from 'react'

interface SkeletonProps {
  width?: string | number
  height?: string | number
  variant?: 'default' | 'text' | 'circular'
  className?: string
  style?: React.CSSProperties
}

export function Skeleton({
  width,
  height,
  variant = 'default',
  className = '',
  style: styleProp,
}: SkeletonProps) {
  const style: React.CSSProperties = { ...styleProp }

  if (width !== undefined) {
    style.width = typeof width === 'number' ? `${width}px` : width
  }
  if (height !== undefined) {
    style.height = typeof height === 'number' ? `${height}px` : height
  }
  if (variant === 'circular') {
    style.borderRadius = '50%'
  }

  const classes = [
    'skeleton',
    variant === 'text' ? 'skeleton--text' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div
      className={classes}
      style={style}
      aria-hidden="true"
      role="presentation"
    />
  )
}

/** 아이템 카드 그리드 스켈레톤 (여러 개) */
interface SkeletonGridProps {
  count?: number
  columns?: 2 | 3 | 4
}

export function SkeletonGrid({ count = 8, columns = 4 }: SkeletonGridProps) {
  return (
    <div
      className={`grid grid--${columns}`}
      aria-label="콘텐츠 로딩 중"
      aria-busy="true"
    >
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="item-card" aria-hidden="true">
          <div
            className="item-card__thumb"
            style={{ paddingTop: '66.67%', position: 'relative' }}
          >
            <div
              className="skeleton"
              style={{ position: 'absolute', inset: 0 }}
            />
          </div>
          <div className="item-card__body">
            <div
              className="item-card__seller"
              style={{ marginBottom: 'var(--space-2)' }}
            >
              <Skeleton variant="circular" width={22} height={22} />
              <Skeleton variant="text" width={60} height={12} />
            </div>
            <Skeleton variant="text" height={14} style={{ marginBottom: 'var(--space-2)' }} />
            <Skeleton variant="text" width="65%" height={14} style={{ marginBottom: 'var(--space-3)' }} />
            <Skeleton variant="text" width="45%" height={16} />
          </div>
        </div>
      ))}
    </div>
  )
}
