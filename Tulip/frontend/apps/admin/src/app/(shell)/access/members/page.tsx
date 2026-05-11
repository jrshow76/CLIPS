'use client';

/**
 * 회원 관리 — 목록 화면 (`/access/members`)
 *
 * - FilterBar: 키워드·상태·도서관·회원유형
 * - DataTable: 회원번호·이름·유형·도서관·상태·가입일·작업
 * - Pagination
 * - "회원 등록" 버튼 → FormModal
 */
import { useHasScope } from '@tulip/auth';
import {
  useCreateMemberMutation,
  useLibrariesQuery,
  useMembersQuery,
  type Member,
  type MemberListQuery,
  type MemberStatus,
  type MemberType,
} from '@tulip/api-client';
import {
  AccessDenied,
  Badge,
  Button,
  DataTable,
  EmptyState,
  FilterBar,
  FormModal,
  Icon,
  Pagination,
  PageHeader,
  Select,
  StatusBadge,
  useToast,
  type Column,
} from '@tulip/ui';
import { Plus, UserRound } from 'lucide-react';
import Link from 'next/link';
import { useMemo, useRef, useState } from 'react';

import { MemberForm, type MemberFormHandle } from './_components/MemberForm';

const PAGE_SIZE = 20;

const STATUS_OPTIONS: { value: '' | MemberStatus; label: string }[] = [
  { value: '', label: '전체 상태' },
  { value: 'ACTIVE', label: '정상' },
  { value: 'SUSPENDED', label: '정지' },
  { value: 'EXPIRED', label: '만료' },
  { value: 'WITHDRAWN', label: '탈퇴' },
];

const TYPE_OPTIONS: { value: '' | MemberType; label: string }[] = [
  { value: '', label: '전체 유형' },
  { value: 'ADULT', label: '성인' },
  { value: 'YOUTH', label: '청소년' },
  { value: 'CHILD', label: '어린이' },
  { value: 'STAFF', label: '직원' },
  { value: 'GUEST', label: '게스트' },
];

export default function MembersPage() {
  const canRead = useHasScope('member:read');
  const canWrite = useHasScope('member:write');

  if (!canRead) {
    return (
      <>
        <PageHeader
          title="회원 관리"
          breadcrumb={[{ label: '홈', href: '/' }, { label: '회원/이용' }, { label: '회원 관리' }]}
        />
        <div className="p-6">
          <AccessDenied requiredScope="회원 조회(member:read)" />
        </div>
      </>
    );
  }

  return <MembersPageInner canWrite={canWrite} />;
}

function MembersPageInner({ canWrite }: { canWrite: boolean }) {
  const { show } = useToast();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<{
    q: string;
    status: '' | MemberStatus;
    libraryId: string;
    memberType: '' | MemberType;
  }>({ q: '', status: '', libraryId: '', memberType: '' });

  const params: MemberListQuery = useMemo(
    () => ({
      q: filters.q || undefined,
      status: filters.status || undefined,
      libraryId: filters.libraryId || undefined,
      memberType: filters.memberType || undefined,
      page,
      size: PAGE_SIZE,
    }),
    [filters, page],
  );

  const { data, isLoading, isError, error, refetch } = useMembersQuery(params);
  const librariesQuery = useLibrariesQuery({ size: 100 });

  const [createOpen, setCreateOpen] = useState(false);
  const formRef = useRef<MemberFormHandle>(null);
  const createMutation = useCreateMemberMutation();

  const libraryOptions = useMemo(
    () => [
      { value: '', label: '전체 도서관' },
      ...((librariesQuery.data?.items ?? []).map((l) => ({ value: l.id, label: l.name }))),
    ],
    [librariesQuery.data?.items],
  );

  function resetFilters() {
    setFilters({ q: '', status: '', libraryId: '', memberType: '' });
    setPage(1);
  }

  const columns: Column<Member>[] = [
    {
      id: 'memberNumber',
      header: '회원번호',
      cell: (m) => <span className="font-medium text-neutral-900">{m.memberNumber}</span>,
      width: 140,
    },
    {
      id: 'name',
      header: '이름',
      cell: (m) => (
        <Link
          href={`/access/members/${m.id}`}
          className="text-primary-700 hover:underline focus-visible:outline-none focus-visible:shadow-focus rounded"
        >
          {m.name}
        </Link>
      ),
    },
    {
      id: 'memberType',
      header: '유형',
      cell: (m) => <Badge tone="primary" variant="soft" size="sm">{memberTypeLabel(m.memberType)}</Badge>,
      width: 100,
    },
    {
      id: 'library',
      header: '도서관',
      cell: (m) => m.libraryName ?? m.libraryId,
      width: 160,
    },
    {
      id: 'status',
      header: '상태',
      cell: (m) => <StatusBadge status={m.status} />,
      width: 100,
    },
    {
      id: 'joinedAt',
      header: '가입일',
      cell: (m) => formatDate(m.joinedAt),
      width: 120,
    },
    {
      id: 'actions',
      header: <span className="sr-only">작업</span>,
      cell: (m) => (
        <Link
          href={`/access/members/${m.id}`}
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
        title="회원 관리"
        description="이용자 회원 등록·조회·상태 관리를 수행합니다."
        breadcrumb={[
          { label: '홈', href: '/' },
          { label: '회원/이용', href: '/access/members' },
          { label: '회원 관리' },
        ]}
        actions={
          canWrite ? (
            <Button
              variant="primary"
              leftIcon={<Icon as={Plus} size="sm" />}
              onClick={() => setCreateOpen(true)}
            >
              회원 등록
            </Button>
          ) : undefined
        }
      />

      <div className="flex flex-col gap-4 p-6">
        <FilterBar
          defaultKeyword={filters.q}
          placeholder="회원번호 · 이름 · 연락처 검색"
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
                  setFilters((f) => ({ ...f, status: e.target.value as MemberStatus | '' }));
                  setPage(1);
                }}
                options={STATUS_OPTIONS}
                size="sm"
              />
              <Select
                aria-label="도서관"
                value={filters.libraryId}
                onChange={(e) => {
                  setFilters((f) => ({ ...f, libraryId: e.target.value }));
                  setPage(1);
                }}
                options={libraryOptions}
                size="sm"
              />
              <Select
                aria-label="회원 유형"
                value={filters.memberType}
                onChange={(e) => {
                  setFilters((f) => ({ ...f, memberType: e.target.value as MemberType | '' }));
                  setPage(1);
                }}
                options={TYPE_OPTIONS}
                size="sm"
              />
            </>
          }
        />

        {isError && (
          <div className="rounded-lg border border-danger bg-danger-50 px-4 py-3 text-[13px] text-danger">
            회원 목록을 불러오지 못했습니다 ({error?.code ?? 'ERR'}).{' '}
            <button
              type="button"
              className="ml-1 underline hover:opacity-80"
              onClick={() => void refetch()}
            >
              다시 시도
            </button>
          </div>
        )}

        <DataTable<Member>
          columns={columns}
          data={data?.items ?? []}
          rowKey={(m) => m.id}
          loading={isLoading}
          empty={
            <EmptyState
              icon={<Icon as={UserRound} size="xl" />}
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
        title="회원 등록"
        description="신규 회원의 기본 정보를 입력하세요."
        submitText="등록"
        submitting={createMutation.isPending}
        onClose={() => setCreateOpen(false)}
        onSubmit={() => formRef.current?.submit()}
      >
        <MemberForm
          ref={formRef}
          onValid={(values) =>
            createMutation.mutate(values as Parameters<typeof createMutation.mutate>[0], {
              onSuccess: () => {
                show({ type: 'success', title: '회원이 등록되었습니다.' });
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

function memberTypeLabel(t: MemberType): string {
  switch (t) {
    case 'ADULT':
      return '성인';
    case 'YOUTH':
      return '청소년';
    case 'CHILD':
      return '어린이';
    case 'STAFF':
      return '직원';
    case 'GUEST':
      return '게스트';
  }
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('ko-KR');
  } catch {
    return iso;
  }
}
