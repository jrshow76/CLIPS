import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'WebReporter — 웹 리포팅 도구',
  description: 'PDF 리포트 디자이너 · 뷰어 · 인쇄',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body style={{ height: '100vh', overflow: 'hidden' }}>{children}</body>
    </html>
  );
}
