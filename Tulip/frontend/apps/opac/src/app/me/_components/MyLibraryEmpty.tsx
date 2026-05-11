'use client';

import { EmptyState, Icon } from '@tulip/ui';
import { Library } from 'lucide-react';

export function MyLibraryEmpty() {
  return (
    <EmptyState
      icon={<Icon as={Library} size="xl" />}
      title="로그인이 필요합니다"
      description="Phase 1-B에서 OAuth2 PKCE 로그인 흐름이 연결됩니다."
    />
  );
}
