import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'
import { GNB } from '@/components/common/GNB'

export const metadata: Metadata = {
  title: {
    default: 'Shelfy - 당신의 선반을 세상에 공개하세요',
    template: '%s | Shelfy',
  },
  description:
    '자신의 물건을 선반에 등록하고, 다른 사용자가 둘러보며 구매하거나 구독할 수 있는 플랫폼',
  keywords: ['shelfy', '디지털 콘텐츠', '구독', '판매', '선반'],
  openGraph: {
    title: 'Shelfy',
    description: '당신의 선반을 세상에 공개하세요',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="ko">
      <body>
        <Providers>
          <GNB />
          {children}
        </Providers>
      </body>
    </html>
  )
}
