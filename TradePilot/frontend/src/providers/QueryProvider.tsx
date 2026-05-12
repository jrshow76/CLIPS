'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { type ReactNode, useState } from 'react';

import { STALE_TIME } from '@/lib/constants';

export function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: STALE_TIME.DEFAULT,
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
              // 인증/권한 에러는 재시도 무의미
              const code = (error as { code?: string })?.code;
              if (code === 'E0001' || code === 'E0002' || code === 'E0006') return false;
              return failureCount < 2;
            },
          },
          mutations: {
            retry: 0,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      {children}
      {process.env.NEXT_PUBLIC_APP_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}
