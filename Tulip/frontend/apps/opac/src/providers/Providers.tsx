'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { QUERY_DEFAULT_GC_TIME, QUERY_DEFAULT_STALE_TIME } from '@tulip/config';
import { ToastProvider } from '@tulip/ui';
import { useState, type ReactNode } from 'react';

import { AuthProvider } from './AuthProvider';

/**
 * OPAC 전역 Provider.
 * - QueryClient (TanStack Query)
 * - AuthProvider (Phase 1-B — iam-service 세션 복원)
 * - ToastProvider
 */
export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: QUERY_DEFAULT_STALE_TIME,
            gcTime: QUERY_DEFAULT_GC_TIME,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <ToastProvider>{children}</ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
