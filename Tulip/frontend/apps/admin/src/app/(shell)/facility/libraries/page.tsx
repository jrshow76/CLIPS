'use client';

/**
 * 도서관 관리 — 목록 화면 (`/facility/libraries`)
 */
import {
  useCreateLibraryMutation,
  useLibrariesQuery,
  type Library,
  type LibraryKind,
  type LibraryListQuery,
  type LibraryStatus,
} from '@tulip/api-client';
import { useHasScope } from '@tulip/auth';
import {
  AccessDenied,
  Badge,
  Button,
  DataTable,
  EmptyState,
  FilterBar,
  FormModal,
  Icon,
  PageHeader,
  Pagination,
  Select,
  StatusBadge,
  useToast,
  type Column,
} from '@tulip/ui';
import { Building2, Plus } from 'lucide-react';
import Link from 'next/link';
import { useMemo, useRef, useState } from 'react';

import { LibraryForm, type LibraryFormHandle } from './_components/LibraryForm';

const PAGE_SIZE = 20;

const STATUS_OPTIONS: { value: '' | LibraryStatus; label: string }[] = [
  { value: '', label: '전체 상태' },
  { value: 'ACTIVE', label: '운영중' },
  { value: 'INACTIVE', label: '비활성' },
  { value: 'CLOSED', label: '폐쇄' },
];

const KIND_OPTIONS: { value: '' | LibraryKind; label: string }[] = [
  { value: '', label: '전체 유형' },
  { value: 'MAIN', label: '본관' },
  { value: 'BRANCH', label: '분관' },
  { value: 'BOOK_MOBILE', label: '이동도서관' },
  { value: 'PARTNER', label: '협력기관' },
];

export default function LibrariesPage() {
  const canRead = useHasScope('tenant:read');
  const canWrite = useHasScope('tenant:write');

  if (!canRead) {
    return (
      <>
        <PageHeader
          title="도서관 관리"
          breadcrumb={[{ label: '홈', href: '/' }, { label: '시설' }, { label: '도서관 관리' }]}
        />
        <div className="p-6">
          <AccessDenied requiredScope="테넌트 조회(tenant:read)" />
        </div>
      </>
    );
  }

  return <LibrariesPageInner canWrite={canWrite} />;
}

function LibrariesPageInner({ canWrite }: { canWrite: boolean }) {
  const { show } = useToast();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<{
    q: string;
    status: '' | LibraryStatus;
    kind: '' | LibraryKind;
  }>({ q: '', status: '', kind: '' });

  const params: LibraryListQuery = useMemo(
    () => ({
      q: filters.q || undefined,
      status: filters.status || undefined,
      kind: filters.kind || undefined,
      page,
      size: PAGE_SIZE,
    }),
    [filters, page],
  );

  const { data, isLoading, isError, error, refetch } = useLibrariesQuery(params);
  const [createOpen, setCreateOpen] = useState(false);
  const formRef = useRef<LibraryFormHandle>(null);
  const createMutation = useCreateLibraryMutation();

  function resetFilters() {
    setFilters({ q: '', status: '', kind: '' });
    setPage(1);
  }

  const columns: Column<Library>[] = [
    {
      id: 'code',
      header: '코드',
      cell: (l) => <span className="font-medium text-neutral-900">{l.code}</span>,
      width: 120,
    },
    {
      id: 'name',
      header: '도서관',
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
      cell: (l) => <Badge tone="primary" variant="soft" size="sm">{kindLabel(l.kind)}</Badge>,
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
    {
      id: 'phone',
      header: '전화',
      cell: (l) => l.phone ?? '—',
      width: 140,
    },
    {
      id: 'actions',
      header: <span className="sr-only">작업</span>,
      cell: (l) => (
        <Link
          href={`/facility/libraries/${l.id}`}
          className="text-[12px] text-primary-600 hover:underline"
        >
          상세
        </Link>
      ),
      align: 'right',
      width: 70,
    },
  ];

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader
        title="도서관 관리"
        description="본관·분관·이동도서관 등 시설 단위 마스터를 관리합니다."
        breadcrumb={[
          { label: '홈', href: '/' },
          { label: '시설', href: '/facility/libraries' },
          { label: '도서관 관리' },
        ]}
        actions={
          canWrite ? (
            <Button
              variant="primary"
              leftIcon={<Icon as={Plus} size="sm" />}
              onClick={() => setCreateOpen(true)}
            >
              도서관 등록
            </Button>
          ) : undefined
        }
      />

      <div className="flex flex-col gap-4 p-6">
        <FilterBar
          defaultKeyword={filters.q}
          placeholder="이름 · 코드 검색"
          onSearch={(q) => {
            setFilters((f) => ({ ...f, q }));
            setPage(1);
          }}
          onReset={resetFilters}
          filters={
            <>
              <Select
                aria-label="상태"
                value={filters.status}
                onChange={(e) => {
                  setFilters((f) => ({ ...f, status: e.target.value as LibraryStatus | '' }));
                  setPage(1);
                }}
                options={STATUS_OPTIONS}
                size="sm"
              />
              <Select
                aria-label="유형"
                value={filters.kind}
                onChange={(e) => {
                  setFilters((f) => ({ ...f, kind: e.target.value as LibraryKind | '' }));
                  setPage(1);
                }}
                options={KIND_OPTIONS}
                size="sm"
              />
            </>
          }
        />

        {isError && (
          <div className="rounded-lg border border-danger bg-danger-50 px-4 py-3 text-[13px] text-danger">
            도서관 목록을 불러오지 못했습니다 ({error?.code ?? 'ERR'}).{' '}
            <button
              type="button"
              className="ml-1 underline hover:opacity-80"
              onClick={() => void refetch()}
            >
              다시 시도
            </button>
          </div>
        )}

        <DataTable<Library>
          columns={columns}
          data={data?.items ?? []}
          rowKey={(l) => l.id}
          loading={isLoading}
          empty={
            <EmptyState
              icon={<Icon as={Building2} size="xl" />}
              title="검색 결과가 없습니다"
              description="검색어·필터를 조정해 보세요."
            />
          }
        />

        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-neutral-500">
              총 {total.toLocaleString()}건 · {page} / {totalPages} 페이지
            </span>
            <Pagination current={page} totalPages={totalPages} onChange={setPage} />
          </div>
        )}
      </div>

      <FormModal
        open={createOpen}
        title="도서관 등록"
        description="새 도서관 시설의 기본 정보를 입력하세요."
        submitText="등록"
        submitting={createMutation.isPending}
        onClose={() => setCreateOpen(false)}
        onSubmit={() => formRef.current?.submit()}
      >
        <LibraryForm
          ref={formRef}
          onValid={(values) =>
            createMutation.mutate(values as Parameters<typeof createMutation.mutate>[0], {
              onSuccess: () => {
                show({ type: 'success', title: '도서관이 등록되었습니다.' });
                setCreateOpen(false);
              },
              onError: (e) =>
                show({
                  type: 'danger',
                  title: '등록 실패',
                  description: e.userMessage ?? e.message,
                }),
            })
          }
        />
      </FormModal>
    </>
  );
}

function kindLabel(k: LibraryKind): string {
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
