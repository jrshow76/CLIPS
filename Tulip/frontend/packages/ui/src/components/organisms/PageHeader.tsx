/**
 * PageHeader — 페이지 상단 타이틀·액션 영역.
 *
 * 사용: Admin 페이지·OPAC 검색 결과 페이지 등.
 */
import { type ReactNode } from 'react';

import { cn } from '../../lib/cn';

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  breadcrumb?: BreadcrumbItem[];
  /** 우측 액션 영역 */
  actions?: ReactNode;
  /** 페이지 하단 탭/필터 슬롯 */
  tabs?: ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  breadcrumb,
  actions,
  tabs,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn('border-b border-neutral-200 bg-surface-card px-6 py-4', className)}>
      {breadcrumb && breadcrumb.length > 0 && (
        <nav aria-label="breadcrumb" className="mb-2">
          <ol className="flex flex-wrap items-center gap-1 text-[12px] text-neutral-500">
            {breadcrumb.map((item, idx) => {
              const last = idx === breadcrumb.length - 1;
              return (
                <li key={`${item.label}-${idx}`} className="flex items-center gap-1">
                  {item.href && !last ? (
                    <a
                      href={item.href}
                      className="hover:text-neutral-800 hover:underline focus-visible:outline-none focus-visible:shadow-focus rounded"
                    >
                      {item.label}
                    </a>
                  ) : (
                    <span aria-current={last ? 'page' : undefined} className={last ? 'text-neutral-700' : ''}>
                      {item.label}
                    </span>
                  )}
                  {!last && <span aria-hidden="true">/</span>}
                </li>
              );
            })}
          </ol>
        </nav>
      )}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-h1 text-neutral-900">{title}</h1>
          {description && (
            <p className="mt-1 text-[14px] text-neutral-600">{description}</p>
          )}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      {tabs && <div className="mt-4">{tabs}</div>}
    </div>
  );
}
