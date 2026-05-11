'use client';

import { EmptyState, Icon } from '@tulip/ui';
import { BookOpen } from 'lucide-react';

export function BookDetailEmpty() {
  return (
    <EmptyState
      icon={<Icon as={BookOpen} size="xl" />}
      title="아직 자료 상세 API가 연결되지 않았습니다"
      description="Phase 1-B에서 서지 상세·소장 정보·예약 기능이 연결됩니다."
    />
  );
}
