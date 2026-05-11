'use client';

import { EmptyState, Icon } from '@tulip/ui';
import { SearchX } from 'lucide-react';

export function EmptyPlaceholder() {
  return (
    <EmptyState
      icon={<Icon as={SearchX} size="xl" />}
      title="아직 검색 API가 연결되지 않았습니다"
      description="Phase 1-B에서 OPAC 검색 API와 연동됩니다."
    />
  );
}
