import type { Metadata, Viewport } from 'next';

import { Providers } from '@/providers/Providers';

import './globals.css';

export const metadata: Metadata = {
  title: 'TradePilot · 자동주식매매',
  description: '전략 기반 자동매매와 시뮬레이션을 한 화면에서. AI 추천, 차트 분석, 백테스트.',
  applicationName: 'TradePilot',
  authors: [{ name: 'TradePilot Team' }],
  robots: { index: false },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#0b0f17',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" data-theme="dark" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
