'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const items = [
  { href: '/search', label: '검색' },
  { href: '/me', label: 'MyLibrary' },
  { href: '/login', label: '로그인' },
];

export function NavLinks() {
  const pathname = usePathname();
  return (
    <nav aria-label="주요 메뉴">
      <ul role="list" className="flex items-center gap-1 sm:gap-2">
        {items.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={[
                  'inline-flex h-9 items-center rounded-md px-3 text-[13px] font-medium',
                  'focus-visible:outline-none focus-visible:shadow-focus',
                  active
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-neutral-700 hover:bg-neutral-100',
                ].join(' ')}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
