'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useAuth } from '@/lib/hooks/useAuth';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/map', label: '지도' },
  { href: '/places', label: '장소 목록' },
  { href: '/stats', label: '통계' },
];

export default function GNB() {
  const pathname = usePathname();
  const { isAuthenticated, user } = useAuthStore();
  const { logoutMutation } = useAuth();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <nav className="h-[60px] bg-white border-b border-[#E7E5E4] flex items-center px-6 gap-4 z-[100] flex-shrink-0 sticky top-0">
      {/* 로고 */}
      <Link
        href="/map"
        className="text-[20px] font-extrabold text-[#F97316] flex items-center gap-1.5 no-underline"
      >
        <span>🗺️</span>
        <span>발자국</span>
      </Link>

      {/* 내비게이션 */}
      <div className="flex gap-1 ml-4 max-md:hidden">
        {navItems.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'px-3 py-1.5 rounded-lg text-[14px] font-medium transition-colors no-underline',
              pathname === href || pathname.startsWith(href + '/')
                ? 'bg-[#FFF8F0] text-[#F97316]'
                : 'text-[#78716C] hover:bg-[#FFF8F0] hover:text-[#F97316]'
            )}
          >
            {label}
          </Link>
        ))}
      </div>

      {/* 우측 액션 */}
      <div className="ml-auto flex items-center gap-2">
        {mounted && isAuthenticated ? (
          <>
            <Link
              href="/places/new"
              className="inline-flex items-center gap-1 px-3.5 py-[7px] bg-[#F97316] hover:bg-[#EA580C] text-white text-[13px] font-semibold rounded-lg transition-colors no-underline"
            >
              <span>＋</span>
              <span>장소 등록</span>
            </Link>
            <button
              onClick={() => logoutMutation.mutate()}
              className="px-3.5 py-[7px] bg-transparent text-[#78716C] border border-[#E7E5E4] text-[13px] font-semibold rounded-lg hover:bg-[#F5F5F0] transition-colors cursor-pointer"
            >
              👤 {user?.nickname ?? '내 정보'}
            </button>
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="px-3.5 py-[7px] text-[#78716C] border border-[#E7E5E4] text-[13px] font-semibold rounded-lg hover:bg-[#F5F5F0] transition-colors no-underline"
            >
              로그인
            </Link>
            <Link
              href="/signup"
              className="px-3.5 py-[7px] bg-[#F97316] hover:bg-[#EA580C] text-white text-[13px] font-semibold rounded-lg transition-colors no-underline"
            >
              회원가입
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
