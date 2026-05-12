'use client';

import { ChevronRight } from 'lucide-react';
import Link from 'next/link';
import { type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface BreadcrumbItem {
  label: ReactNode;
  href?: string;
}

export function BreadcrumbNav({ items, className }: { items: BreadcrumbItem[]; className?: string }) {
  return (
    <nav className={cn('flex items-center gap-1 text-xs text-subtle', className)} aria-label="브레드크럼">
      {items.map((it, i) => (
        <span key={i} className="row items-center gap-1">
          {it.href ? (
            <Link href={it.href} className="hover:text-fg-1">
              {it.label}
            </Link>
          ) : (
            <span className="text-fg-1">{it.label}</span>
          )}
          {i < items.length - 1 && <ChevronRight className="h-3 w-3" />}
        </span>
      ))}
    </nav>
  );
}
