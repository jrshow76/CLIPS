import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import { Providers } from '@/providers/Providers';

import './globals.css';

export const metadata: Metadata = {
  title: 'Tulip+ 관리자',
  description: '도서관통합관리시스템 — 사서 관리자 콘솔',
  applicationName: 'Tulip+ Admin',
  authors: [{ name: 'Tulip+ Team' }],
  robots: { index: false, follow: false },
};

export const viewport = {
  themeColor: '#DB2777',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="bg-surface-app text-neutral-900 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
