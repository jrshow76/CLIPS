'use client';

/**
 * BranchSection — 본관 도서관 상세 화면의 "분관" 섹션.
 *
 * 본관 ID 하위의 분관 목록을 나열한다.
 */
import {
  useLibrariesQuery,
  type Library,
} from '@tulip/api-client';
import {
  DataTable,
  EmptyState,
  Icon,
  Spinner,
  StatusBadge,
  type Column,
} from '@tulip/ui';
import { Building2 } from 'lucide-react';
import Link from 'next/link';

export interface BranchSectionProps {
  parentId: string;
}

export function BranchSection({ parentId }: BranchSectionProps) {
  const { data, isLoading } = useLibrariesQuery({ parentId, size: 100 });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-2 py-6 text-neutral-500">
        <Spinner size="sm" /> 분관 목록 불러오는 중…
      </div>
    );
  }

  const items = data?.items ?? [];

  if (items.length === 0) {
    return (
      <EmptyState
        icon={<Icon as={Building2} size="xl" />}
        title="등록된 분관이 없습니다"
        description="이 본관에 소속된 분관·이동도서관·협력기관이 표시됩니다."
      />
    );
  }

  const columns: Column<Library>[] = [
    { id: 'code', header: '코드', cell: (l) => l.code, width: 120 },
    {
      id: 'name',
      header: '이름',
      cell: (l) => (
        <Link
          href={`/facility/libraries/${l.id}`}
          className="text-primary-700 hover:underline"
        >
          {l.name}
        </Link>
      ),
    },
    {
      id: 'kind',
      header: '유형',
      cell: (l) => kindLabel(l.kind),
      width: 100,
    },
    {
      id: 'status',
      header: '상태',
      cell: (l) => <StatusBadge status={l.status} />,
      width: 100,
    },
    {
      id: 'address',
      header: '주소',
      cell: (l) => l.address ?? '—',
    },
  ];

  return <DataTable<Library> columns={columns} data={items} rowKey={(l) => l.id} density="compact" />;
}

function kindLabel(k: Library['kind']): string {
  switch (k) {
    case 'MAIN':
      return '본관';
    case 'BRANCH':
      return '분관';
    case 'BOOK_MOBILE':
      return '이동';
    case 'PARTNER':
      return '협력';
  }
}
