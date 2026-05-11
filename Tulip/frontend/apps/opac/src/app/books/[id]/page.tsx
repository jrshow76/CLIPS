import { Badge, PageHeader } from '@tulip/ui';

import { BookDetailEmpty } from './_components/BookDetailEmpty';

export const metadata = { title: '자료 상세 — Tulip+ OPAC' };

interface BookDetailProps {
  params: Promise<{ id: string }>;
}

export default async function BookDetailPage({ params }: BookDetailProps) {
  const { id } = await params;
  return (
    <div className="container-opac mx-auto max-w-[1200px] px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="자료 상세"
        description={`자료 ID: ${id}`}
        breadcrumb={[
          { label: '홈', href: '/' },
          { label: '검색', href: '/search' },
          { label: '자료 상세' },
        ]}
        actions={
          <Badge tone="primary" variant="soft">
            Phase 1-A 자리표시자
          </Badge>
        }
      />
      <div className="mt-6">
        <BookDetailEmpty />
      </div>
    </div>
  );
}
