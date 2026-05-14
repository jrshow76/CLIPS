import type { Metadata, Viewport } from 'next';

import { Providers } from '@/providers/Providers';

import './globals.css';

export const metadata: Metadata = {
  title: 'TradePilot · 자동주식매매',
  description: '전략 기반 자동매매와 시뮬레이션을 한 화면에서. AI 추천, 차트 분석, 백테스트.',
  applicationName: 'TradePilot',
  authors: [{ name: 'TradePilot Team' }],
  robots: { index: false },
  manifest: '/manifest.webmanifest',
  appleWebApp: {
    capable: true,
    title: 'TradePilot',
    statusBarStyle: 'black-translucent',
    startupImage: ['/icons/icon-512-placeholder.svg'],
  },
  formatDetection: {
    telephone: false,
  },
  icons: {
    icon: [
      { url: '/icons/icon-192-placeholder.svg', sizes: '192x192', type: 'image/svg+xml' },
      { url: '/icons/icon-512-placeholder.svg', sizes: '512x512', type: 'image/svg+xml' },
    ],
    apple: [
      { url: '/icons/icon-192-placeholder.svg', sizes: '192x192', type: 'image/svg+xml' },
    ],
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  viewportFit: 'cover',
  themeColor: [
    { media: '(prefers-color-scheme: dark)', color: '#0b0f17' },
    { media: '(prefers-color-scheme: light)', color: '#f8fafc' },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" data-theme="dark" suppressHydrationWarning>
      <head>
        {/* PWA / iOS Safari 메타 (Next 14 Metadata API 가 일부 미커버) */}
        <meta name="application-name" content="TradePilot" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-title" content="TradePilot" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="msapplication-TileColor" content="#0b0f17" />
        <meta name="msapplication-tap-highlight" content="no" />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
