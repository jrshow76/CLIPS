'use client';

import { useAuth } from '@tulip/auth';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

const publicItems = [
  { href: '/search', label: '검색' },
  { href: '/me', label: 'MyLibrary' },
];

export function NavLinks() {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <nav aria-label="주요 메뉴">
      <ul role="list" className="flex items-center gap-1 sm:gap-2">
        {publicItems.map((item) => {
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
        {isAuthenticated ? (
          <li className="flex items-center gap-1 pl-2 text-[13px] text-neutral-700">
            <span aria-label="로그인 사용자">{user?.name}</span>
            <button
              type="button"
              onClick={() => {
                void logout().then(() => router.replace('/'));
              }}
              className="inline-flex h-9 items-center rounded-md px-3 text-[13px] font-medium text-neutral-700 hover:bg-neutral-100 focus-visible:outline-none focus-visible:shadow-focus"
            >
              로그아웃
            </button>
          </li>
        ) : (
          <li>
            <Link
              href="/login"
              aria-current={pathname.startsWith('/login') ? 'page' : undefined}
              className={[
                'inline-flex h-9 items-center rounded-md px-3 text-[13px] font-medium',
                'focus-visible:outline-none focus-visible:shadow-focus',
                pathname.startsWith('/login')
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-neutral-700 hover:bg-neutral-100',
              ].join(' ')}
            >
              로그인
            </Link>
          </li>
        )}
      </ul>
    </nav>
  );
}
