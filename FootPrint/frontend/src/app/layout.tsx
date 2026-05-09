import type { Metadata } from 'next';
import Script from 'next/script';
import './globals.css';
import QueryProvider from '@/components/layout/QueryProvider';

export const metadata: Metadata = {
  title: '발자국 | 나의 장소 기록',
  description: '내가 다녀온 장소를 지도 위에 기록하고 관리하는 서비스',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const kakaoApiKey = process.env.NEXT_PUBLIC_KAKAO_MAP_KEY ?? '';

  return (
    <html lang="ko">
      <head>
        {kakaoApiKey && (
          <Script
            src={`//dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoApiKey}&autoload=false`}
            strategy="beforeInteractive"
          />
        )}
      </head>
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
