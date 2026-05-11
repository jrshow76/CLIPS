'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { QUERY_DEFAULT_GC_TIME, QUERY_DEFAULT_STALE_TIME } from '@tulip/config';
import { useState, type ReactNode } from 'react';

export function QueryProvider({ children }: { children: ReactNode }) {
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
          mutations: {
            retry: 0,
          },
        },
      }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
