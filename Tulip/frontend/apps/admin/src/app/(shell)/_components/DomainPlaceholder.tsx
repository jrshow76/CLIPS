'use client';

import { Badge, EmptyState, Icon, PageHeader } from '@tulip/ui';
import { Construction } from 'lucide-react';

import type { DomainCode } from '@tulip/config';
import { DOMAINS } from '@tulip/config';

/**
 * 도메인 자리표시자 페이지 — Phase 1-A 동안 모든 도메인 라우트가 공유.
 */
export function DomainPlaceholder({ domain }: { domain: DomainCode }) {
  const meta = DOMAINS[domain];
  return (
    <>
      <PageHeader
        title={`${meta.name} (${meta.abbr})`}
        description={`${meta.englishName} 도메인 — Phase 1-A 단계에서는 자리표시자 페이지입니다.`}
        breadcrumb={[{ label: '홈', href: '/' }, { label: meta.name }]}
        actions={
          <Badge
            tone="neutral"
            variant="outline"
            style={{ borderColor: meta.color, color: meta.color }}
          >
            {meta.abbr}
          </Badge>
        }
      />
      <div className="p-6">
        <EmptyState
          icon={<Icon as={Construction} size="xl" />}
          title="아직 구현되지 않았습니다"
          description={`${meta.name} 도메인 화면은 Phase 1-B 이후 Planner 화면정의서에 따라 점진적으로 추가됩니다.`}
        />
      </div>
    </>
  );
}
