'use client';

import { useAuth } from '@tulip/auth';
import {
  AppHeader,
  AppSidebar,
  Badge,
  DropdownMenu,
  Icon,
  SearchBar,
  type SidebarItem,
} from '@tulip/ui';
import { Bell, Moon, Settings, Sun, UserRound } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useMemo, type ReactNode } from 'react';

import { useTheme } from '@/providers/ThemeProvider';

/**
 * 관리자 AppShell — Sidebar + Header + Main
 * DSN-03 §6.1 AdminShell 템플릿을 구현.
 */
export default function ShellLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { theme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const displayName = user?.name ?? '게스트';

  const sidebarItems: SidebarItem[] = useMemo(
    () => [
      {
        id: 'dashboard',
        label: '대시보드',
        accent: '#DB2777',
        href: '/dashboard',
        active: pathname === '/dashboard',
      },
      {
        id: 'acq',
        label: '수서 (ACQ)',
        accent: '#F97316',
        href: '/acquisition',
        active: pathname.startsWith('/acquisition'),
      },
      {
        id: 'cat',
        label: '목록 (CAT)',
        accent: '#8B5CF6',
        href: '/cataloging',
        active: pathname.startsWith('/cataloging'),
      },
      {
        id: 'cir',
        label: '열람 (CIR)',
        accent: '#0EA5E9',
        href: '/circulation',
        active: pathname.startsWith('/circulation'),
      },
      {
        id: 'col',
        label: '장서 (COL)',
        accent: '#84CC16',
        href: '/collection',
        active: pathname.startsWith('/collection'),
      },
      {
        id: 'acs',
        label: '출입 (ACS)',
        accent: '#EF4444',
        href: '/access',
        active: pathname.startsWith('/access'),
      },
      {
        id: 'fac',
        label: '시설 (FAC)',
        accent: '#14B8A6',
        href: '/facility',
        active: pathname.startsWith('/facility'),
      },
    ],
    [pathname],
  );

  return (
    <div className="flex min-h-dvh w-full">
      <AppSidebar
        items={sidebarItems}
        onNavigate={(item) => item.href && router.push(item.href)}
        header={
          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-neutral-900 hover:opacity-80"
          >
            <span aria-hidden="true" className="text-xl">
              🌷
            </span>
            <span className="text-[15px] font-bold">Tulip+ Admin</span>
          </Link>
        }
        footer={
          <div className="flex items-center gap-2 text-[12px] text-neutral-500">
            <Badge tone="success" variant="soft" size="sm">
              v0.1
            </Badge>
            <span>Phase 1-A</span>
          </div>
        }
        className="hidden lg:flex"
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader
          brand={
            <Link href="/dashboard" className="flex items-center gap-1 lg:hidden">
              <span aria-hidden="true">🌷</span>
              <span className="font-bold">Tulip+</span>
            </Link>
          }
          search={
            <SearchBar
              variant="compact"
              placeholder="회원·자료·메뉴 통합검색 (Ctrl+K)"
              submitLabel="검색"
            />
          }
          actions={
            <>
              <button
                type="button"
                aria-label="알림"
                className="relative rounded p-2 text-neutral-700 hover:bg-neutral-100 focus-visible:outline-none focus-visible:shadow-focus"
              >
                <Icon as={Bell} size="md" />
                <span
                  aria-hidden="true"
                  className="absolute right-1 top-1 inline-block h-2 w-2 rounded-full bg-danger"
                />
              </button>
              <button
                type="button"
                aria-label={theme === 'light' ? '다크 모드로 전환' : '라이트 모드로 전환'}
                onClick={toggle}
                className="rounded p-2 text-neutral-700 hover:bg-neutral-100 focus-visible:outline-none focus-visible:shadow-focus"
              >
                <Icon as={theme === 'light' ? Moon : Sun} size="md" />
              </button>
              <DropdownMenu
                trigger={({ onClick, ...aria }) => (
                  <button
                    type="button"
                    onClick={onClick}
                    {...aria}
                    className="flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] text-neutral-700 hover:bg-neutral-100 focus-visible:outline-none focus-visible:shadow-focus"
                  >
                    <Icon as={UserRound} size="sm" />
                    {displayName}
                  </button>
                )}
                items={[
                  { id: 'profile', label: '내 정보', onSelect: () => router.push('/me') },
                  {
                    id: 'settings',
                    label: '설정',
                    icon: <Icon as={Settings} size="sm" />,
                    onSelect: () => router.push('/settings'),
                  },
                  {
                    id: 'logout',
                    label: '로그아웃',
                    danger: true,
                    onSelect: () => {
                      void logout().then(() => router.replace('/login'));
                    },
                  },
                ]}
              />
            </>
          }
        />
        <main className="flex-1 overflow-x-hidden">{children}</main>
      </div>
    </div>
  );
}
