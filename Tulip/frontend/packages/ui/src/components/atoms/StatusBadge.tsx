/**
 * StatusBadge — 도메인 상태 → Badge 톤 매핑 헬퍼.
 *
 * 사용:
 *   <StatusBadge status="ACTIVE" />
 *   <StatusBadge status="SUSPENDED" />
 *
 * `mapping` prop으로 커스텀 매핑을 주입할 수 있다.
 * 매핑이 없으면 기본 한글 라벨과 톤을 사용한다.
 */
import { type ReactNode } from 'react';

import { Badge, type BadgeProps } from './Badge';

export type StatusTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'primary';

export interface StatusBadgeMapping {
  tone: StatusTone;
  label: ReactNode;
}

/** 시스템 공통 상태 키 → 라벨/톤 매핑 */
const DEFAULT_STATUS_MAP: Record<string, StatusBadgeMapping> = {
  // 회원
  ACTIVE: { tone: 'success', label: '정상' },
  SUSPENDED: { tone: 'warning', label: '정지' },
  EXPIRED: { tone: 'neutral', label: '만료' },
  WITHDRAWN: { tone: 'neutral', label: '탈퇴' },
  // 도서관
  INACTIVE: { tone: 'neutral', label: '비활성' },
  CLOSED: { tone: 'danger', label: '폐쇄' },
  // 대출
  ON_LOAN: { tone: 'info', label: '대출중' },
  RETURNED: { tone: 'success', label: '반납완료' },
  OVERDUE: { tone: 'danger', label: '연체' },
  LOST: { tone: 'danger', label: '분실' },
  RENEWED: { tone: 'info', label: '연장' },
};

export interface StatusBadgeProps extends Omit<BadgeProps, 'tone' | 'children'> {
  status: string;
  /** 외부 매핑을 우선 적용 */
  mapping?: Record<string, StatusBadgeMapping>;
  /** 매핑이 없을 때 기본 라벨 */
  fallbackLabel?: ReactNode;
}

export function StatusBadge({
  status,
  mapping,
  fallbackLabel,
  variant = 'soft',
  size = 'sm',
  ...rest
}: StatusBadgeProps) {
  const m = mapping?.[status] ?? DEFAULT_STATUS_MAP[status];
  return (
    <Badge tone={m?.tone ?? 'neutral'} variant={variant} size={size} {...rest}>
      {m?.label ?? fallbackLabel ?? status}
    </Badge>
  );
}
