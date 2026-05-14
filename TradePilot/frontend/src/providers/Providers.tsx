'use client';

import { type ReactNode } from 'react';

import { Toaster } from '@/components/ui/toaster';

import { AuthProvider } from './AuthProvider';
import { PWAProvider } from './PWAProvider';
import { QueryProvider } from './QueryProvider';
import { RealtimeProvider } from './RealtimeProvider';
import { ThemeProvider } from './ThemeProvider';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <ThemeProvider>
        <AuthProvider>
          <RealtimeProvider>
            <PWAProvider>
              {children}
              <Toaster />
            </PWAProvider>
          </RealtimeProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}
