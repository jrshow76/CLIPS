'use client';

/**
 * AppHeader — 관리자/OPAC 공통 헤더 (DSN-03 §6.1, §6.2)
 *
 * - 좌: 브랜드 로고 + 모바일 메뉴 토글
 * - 중: 검색바 슬롯
 * - 우: 알림 / 테마 / 사용자 메뉴 슬롯
 */
import { Menu } from 'lucide-react';
import { type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Icon } from '../atoms/Icon';

export interface AppHeaderProps {
  /** 브랜드 영역 (로고·서비스명) */
  brand?: ReactNode;
  /** 검색바 슬롯 */
  search?: ReactNode;
  /** 우측 액션 (알림, 사용자 메뉴 등) */
  actions?: ReactNode;
  /** 모바일 사이드바 토글 핸들러 */
  onToggleSidebar?: () => void;
  className?: string;
  /** sticky 헤더 */
  sticky?: boolean;
}

export function AppHeader({
  brand,
  search,
  actions,
  onToggleSidebar,
  className,
  sticky = true,
}: AppHeaderProps) {
  return (
    <header
      className={cn(
        'flex h-14 items-center gap-4 border-b border-neutral-200 bg-surface-card px-4',
        sticky && 'sticky top-0 z-sticky',
        className,
      )}
    >
      {onToggleSidebar && (
        <button
          type="button"
          aria-label="메뉴 열기"
          onClick={onToggleSidebar}
          className="rounded p-1 text-neutral-700 hover:bg-neutral-100 focus-visible:outline-none focus-visible:shadow-focus lg:hidden"
        >
          <Icon as={Menu} size="md" />
        </button>
      )}
      {brand && <div className="flex shrink-0 items-center gap-2">{brand}</div>}
      {search && <div className="hidden flex-1 md:block">{search}</div>}
      <div className="ml-auto flex items-center gap-2">{actions}</div>
    </header>
  );
}
