'use client';

import { type ReactNode } from 'react';

import { Header } from './Header';
import { LiveModeModal } from './LiveModeModal';
import { Sidebar } from './Sidebar';
import { TradeModeBanner } from './TradeModeBanner';

export interface AppShellProps {
  title?: string;
  children: ReactNode;
}

/**
 * 인증된 사용자용 메인 레이아웃.
 * - Sidebar / Header / Main 의 BEM grid 적용
 * - LIVE 모드 배너와 LiveModeModal을 전역에 마운트
 */
export function AppShell({ title, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <Sidebar />
      <Header title={title} />
      <main className="app-shell__main">
        <TradeModeBanner />
        <div className="mt-3">{children}</div>
      </main>
      <LiveModeModal />
    </div>
  );
}
