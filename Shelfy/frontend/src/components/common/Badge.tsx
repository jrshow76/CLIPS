/**
 * Badge 공통 컴포넌트
 * Designer common.css 클래스 기반: .badge, .badge--purchase/subscribe/both/success/warning/error/neutral
 */

import type { ReactNode } from 'react'
import type { SaleType } from '@/types/item'

type BadgeVariant =
  | 'purchase'
  | 'subscribe'
  | 'both'
  | 'success'
  | 'warning'
  | 'error'
  | 'neutral'

interface BadgeProps {
  variant: BadgeVariant
  children: ReactNode
  className?: string
}

/** 판매 유형(SaleType)에서 Badge variant 변환 */
export function saleTypeToBadgeVariant(saleType: SaleType): BadgeVariant {
  const map: Record<SaleType, BadgeVariant> = {
    PURCHASE: 'purchase',
    SUBSCRIBE: 'subscribe',
    BOTH: 'both',
  }
  return map[saleType]
}

/** 판매 유형 한글 레이블 */
export function saleTypeLabel(saleType: SaleType): string {
  const map: Record<SaleType, string> = {
    PURCHASE: '구매',
    SUBSCRIBE: '구독',
    BOTH: '구매+구독',
  }
  return map[saleType]
}

export function Badge({ variant, children, className = '' }: BadgeProps) {
  return (
    <span className={`badge badge--${variant} ${className}`.trim()}>
      {children}
    </span>
  )
}

/** 판매 유형 배지 (SaleType 기반 바로 사용) */
interface SaleTypeBadgeProps {
  saleType: SaleType
  className?: string
}

export function SaleTypeBadge({ saleType, className }: SaleTypeBadgeProps) {
  return (
    <Badge variant={saleTypeToBadgeVariant(saleType)} className={className}>
      {saleTypeLabel(saleType)}
    </Badge>
  )
}
