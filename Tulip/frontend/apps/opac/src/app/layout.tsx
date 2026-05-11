import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import { Providers } from '@/providers/Providers';

import { Footer } from './_components/Footer';
import { Header } from './_components/Header';

import './globals.css';

export const metadata: Metadata = {
  title: 'Tulip+ — 우리도서관 OPAC',
  description: '도서·자료 검색, 예약, MyLibrary 한 곳에서',
  applicationName: 'Tulip+ OPAC',
};

export const viewport = {
  themeColor: '#DB2777',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="flex min-h-dvh flex-col bg-surface-app text-neutral-900 antialiased">
        <Providers>
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
