'use client';

/**
 * AppSidebar — 관리자 좌측 사이드바 (DSN-03 §6.1)
 *
 * - 1·2 레벨 메뉴, 도메인 컬러 표시
 * - collapsed 토글 (모바일은 외부에서 overlay 처리)
 */
import { ChevronDown } from 'lucide-react';
import { useState, type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Icon } from '../atoms/Icon';

export interface SidebarItem {
  id: string;
  label: string;
  /** 1레벨 도메인 액센트 컬러 (hex) */
  accent?: string;
  /** Lucide Icon 컴포넌트 (선택) */
  icon?: ReactNode;
  /** 라우트 경로 */
  href?: string;
  /** 활성 (현재 라우트) */
  active?: boolean;
  /** 하위 메뉴 */
  children?: SidebarItem[];
}

export interface AppSidebarProps {
  items: SidebarItem[];
  /** 메뉴 클릭 핸들러 (Next/Link 등으로 라우팅) */
  onNavigate?: (item: SidebarItem) => void;
  className?: string;
  /** 접힘 상태 */
  collapsed?: boolean;
  /** 상단 영역 (지점 선택 등) */
  header?: ReactNode;
  /** 하단 영역 (사용자 정보 등) */
  footer?: ReactNode;
}

export function AppSidebar({
  items,
  onNavigate,
  className,
  collapsed = false,
  header,
  footer,
}: AppSidebarProps) {
  return (
    <aside
      aria-label="기본 메뉴"
      className={cn(
        'flex flex-col border-r border-neutral-200 bg-surface-card',
        collapsed ? 'w-16' : 'w-60',
        'transition-[width] duration-base',
        className,
      )}
    >
      {header && <div className="border-b border-neutral-200 px-3 py-3">{header}</div>}
      <nav className="flex-1 overflow-y-auto py-2">
        <ul role="list" className="flex flex-col gap-0.5 px-2">
          {items.map((item) => (
            <SidebarRow
              key={item.id}
              item={item}
              onNavigate={onNavigate}
              collapsed={collapsed}
            />
          ))}
        </ul>
      </nav>
      {footer && <div className="border-t border-neutral-200 px-3 py-3">{footer}</div>}
    </aside>
  );
}

function SidebarRow({
  item,
  onNavigate,
  collapsed,
}: {
  item: SidebarItem;
  onNavigate?: (item: SidebarItem) => void;
  collapsed: boolean;
}) {
  const hasChildren = item.children && item.children.length > 0;
  const [open, setOpen] = useState<boolean>(hasChildren ? !!item.active : false);

  return (
    <li>
      <button
        type="button"
        aria-current={item.active ? 'page' : undefined}
        aria-expanded={hasChildren ? open : undefined}
        onClick={() => {
          if (hasChildren) setOpen((v) => !v);
          else onNavigate?.(item);
        }}
        className={cn(
          'flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-[13px]',
          'transition-colors focus-visible:outline-none focus-visible:shadow-focus',
          item.active
            ? 'bg-primary-50 text-primary-700 font-semibold'
            : 'text-neutral-700 hover:bg-neutral-100',
        )}
        title={collapsed ? item.label : undefined}
      >
        {item.accent && (
          <span
            aria-hidden="true"
            className="inline-block h-3 w-1 shrink-0 rounded-sm"
            style={{ backgroundColor: item.accent }}
          />
        )}
        {item.icon && <span className="shrink-0">{item.icon}</span>}
        {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
        {!collapsed && hasChildren && (
          <Icon
            as={ChevronDown}
            size="sm"
            className={cn('transition-transform', open && 'rotate-180')}
          />
        )}
      </button>
      {hasChildren && open && !collapsed && (
        <ul role="list" className="ml-3 mt-0.5 flex flex-col gap-0.5 border-l border-neutral-200 pl-2">
          {item.children!.map((child) => (
            <li key={child.id}>
              <button
                type="button"
                aria-current={child.active ? 'page' : undefined}
                onClick={() => onNavigate?.(child)}
                className={cn(
                  'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px]',
                  'transition-colors focus-visible:outline-none focus-visible:shadow-focus',
                  child.active
                    ? 'bg-primary-50 text-primary-700 font-semibold'
                    : 'text-neutral-600 hover:bg-neutral-100',
                )}
              >
                <span className="flex-1 truncate">{child.label}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
