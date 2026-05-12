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
 * 도메인별 가시화 권한.
 *
 * 각 도메인 메뉴는 사용자 scope에 따라 노출 여부가 결정된다.
 * 빈 배열은 "스코프 검사 면제"(모두 노출)를 의미한다.
 */
const DOMAIN_SCOPES: Record<string, string[]> = {
  dashboard: [],
  acq: ['acq:read'],
  cat: ['cat:read'],
  cir: ['cir:read'],
  col: ['col:read'],
  access: ['member:read'],
  facility: ['tenant:read'],
  codes: ['code:read'],
};

/** 사용자 scope 중 하나라도 일치하면 노출. 요구 scope가 비면 항상 노출. */
function hasAny(userScopes: string[], required: string[]): boolean {
  if (required.length === 0) return true;
  return required.some((s) => userScopes.includes(s));
}

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

  const userScopes = user?.scopes ?? [];

  const sidebarItems: SidebarItem[] = useMemo(() => {
    const all: (SidebarItem & { domain: keyof typeof DOMAIN_SCOPES })[] = [
      {
        id: 'dashboard',
        domain: 'dashboard',
        label: '대시보드',
        accent: '#DB2777',
        href: '/dashboard',
        active: pathname === '/dashboard',
      },
      {
        id: 'access',
        domain: 'access',
        label: '회원/이용 (ACS)',
        accent: '#EF4444',
        href: '/access/members',
        active: pathname.startsWith('/access'),
        children: [
          {
            id: 'access-members',
            label: '회원 관리',
            href: '/access/members',
            active: pathname.startsWith('/access/members'),
          },
        ],
      },
      {
        id: 'facility',
        domain: 'facility',
        label: '시설 (FAC)',
        accent: '#14B8A6',
        href: '/facility/libraries',
        active: pathname.startsWith('/facility'),
        children: [
          {
            id: 'facility-libraries',
            label: '도서관 관리',
            href: '/facility/libraries',
            active: pathname.startsWith('/facility/libraries'),
          },
        ],
      },
      {
        id: 'codes',
        domain: 'codes',
        label: '코드 관리',
        accent: '#6366F1',
        href: '/codes',
        active: pathname.startsWith('/codes'),
      },
      {
        id: 'acq',
        domain: 'acq',
        label: '수서 (ACQ)',
        accent: '#F97316',
        href: '/acquisition',
        active: pathname.startsWith('/acquisition'),
      },
      {
        id: 'cat',
        domain: 'cat',
        label: '목록 (CAT)',
        accent: '#8B5CF6',
        href: '/cataloging',
        active: pathname.startsWith('/cataloging'),
      },
      {
        id: 'cir',
        domain: 'cir',
        label: '열람 (CIR)',
        accent: '#0EA5E9',
        href: '/circulation',
        active: pathname.startsWith('/circulation'),
      },
      {
        id: 'col',
        domain: 'col',
        label: '장서 (COL)',
        accent: '#84CC16',
        href: '/collection',
        active: pathname.startsWith('/collection'),
      },
    ];

    return all
      .filter((item) => hasAny(userScopes, DOMAIN_SCOPES[item.domain] ?? []))
      .map(({ domain: _domain, ...rest }) => rest);
  }, [pathname, userScopes]);

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
                    data-testid="app-user-menu"
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
