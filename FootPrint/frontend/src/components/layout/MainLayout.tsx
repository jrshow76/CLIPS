import { type ReactNode } from 'react';
import GNB from './GNB';
import ToastContainer from '@/components/common/Toast';

interface MainLayoutProps {
  children: ReactNode;
}

export default function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col bg-[#FAFAF8]">
      <GNB />
      <main className="flex-1">{children}</main>
      <ToastContainer />
    </div>
  );
}
