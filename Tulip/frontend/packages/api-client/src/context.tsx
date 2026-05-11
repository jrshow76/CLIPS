'use client';

/**
 * ApiClientProvider — React Context로 BaseClient 싱글톤 주입.
 *
 * 도메인 hook은 직접 BaseClient를 import하지 않고 `useApiClient()`로
 * 주입된 인스턴스를 받는다. 이렇게 하면:
 *  - 테스트 시 mock client 주입이 쉬워진다.
 *  - admin/opac 등 앱별로 baseUrl·basePath가 달라도 동일 hook을 공유한다.
 *  - api-client 패키지가 앱별 싱글톤 import를 강제하지 않는다.
 */
import { createContext, useContext, type ReactNode } from 'react';

import type { BaseClient } from './client';

const ApiClientContext = createContext<BaseClient | null>(null);

export interface ApiClientProviderProps {
  client: BaseClient;
  children: ReactNode;
}

export function ApiClientProvider({ client, children }: ApiClientProviderProps) {
  return <ApiClientContext.Provider value={client}>{children}</ApiClientContext.Provider>;
}

export function useApiClient(): BaseClient {
  const client = useContext(ApiClientContext);
  if (!client) {
    throw new Error(
      'useApiClient는 <ApiClientProvider> 내부에서만 사용할 수 있습니다. ' +
        '앱 루트에 ApiClientProvider를 추가하세요.',
    );
  }
  return client;
}
