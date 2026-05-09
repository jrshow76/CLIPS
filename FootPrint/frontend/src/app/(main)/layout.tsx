'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import MainLayout from '@/components/layout/MainLayout';
import type { ReactNode } from 'react';

export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('accessToken');
    if (!hasToken && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, router]);

  return <MainLayout>{children}</MainLayout>;
}
