'use client';

import { type ReactNode } from 'react';

import { Toaster } from '@/components/ui/toaster';

import { AuthProvider } from './AuthProvider';
import { QueryProvider } from './QueryProvider';
import { RealtimeProvider } from './RealtimeProvider';
import { ThemeProvider } from './ThemeProvider';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <ThemeProvider>
        <AuthProvider>
          <RealtimeProvider>
            {children}
            <Toaster />
          </RealtimeProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}
