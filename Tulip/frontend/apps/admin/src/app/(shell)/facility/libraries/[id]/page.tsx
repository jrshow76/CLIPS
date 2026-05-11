'use client';

/**
 * 도서관 상세 페이지 (`/facility/libraries/{id}`)
 *
 * - 기본 정보 + 분관 목록(본관일 때) + 수정/삭제
 */
import {
  useDeleteLibraryMutation,
  useLibraryQuery,
  useUpdateLibraryMutation,
  type Library,
  type UpdateLibraryInput,
} from '@tulip/api-client';
import { useHasScope } from '@tulip/auth';
import {
  AccessDenied,
  Badge,
  Button,
  ConfirmDialog,
  EmptyState,
  FormModal,
  Icon,
  PageHeader,
  Skeleton,
  StatusBadge,
  Tabs,
  useToast,
} from '@tulip/ui';
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useMemo, useRef, useState } from 'react';

import { BranchSection } from '../_components/BranchSection';
import { LibraryForm, type LibraryFormHandle } from '../_components/LibraryForm';

export default function LibraryDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const canRead = useHasScope('tenant:read');
  const canWrite = useHasScope('tenant:write');
  const router = useRouter();
  const { show } = useToast();

  const libraryQuery = useLibraryQuery(id);
  const updateMutation = useUpdateLibraryMutation();
  const deleteMutation = useDeleteLibraryMutation();

  const [editOpen, setEditOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const formRef = useRef<LibraryFormHandle>(null);

  const library = libraryQuery.data;

  const breadcrumb = useMemo(
    () => [
      { label: '홈', href: '/' },
      { label: '시설', href: '/facility/libraries' },
      { label: '도서관 관리', href: '/facility/libraries' },
      { label: library?.name ?? '상세' },
    ],
    [library?.name],
  );

  if (!canRead) {
    return (
      <>
        <PageHeader title="도서관 상세" breadcrumb={breadcrumb} />
        <div className="p-6">
          <AccessDenied requiredScope="테넌트 조회(tenant:read)" />
        </div>
      </>
    );
  }

  if (libraryQuery.isLoading) {
    return (
      <>
        <PageHeader title="도서관 상세" breadcrumb={breadcrumb} />
        <div className="flex flex-col gap-3 p-6">
          <Skeleton height={32} width={240} />
          <Skeleton height={20} width={360} />
          <Skeleton height={300} />
        </div>
      </>
    );
  }

  if (libraryQuery.isError || !library) {
    return (
      <>
        <PageHeader title="도서관 상세" breadcrumb={breadcrumb} />
        <div className="p-6">
          <EmptyState
            title="도서관 정보를 찾을 수 없습니다"
            description="시설이 삭제되었거나 접근 권한이 없습니다."
            primaryAction={
              <Button
                variant="secondary"
                leftIcon={<Icon as={ArrowLeft} size="sm" />}
                onClick={() => router.push('/facility/libraries')}
              >
                목록으로
              </Button>
            }
          />
        </div>
      </>
    );
  }

  const tabItems = [
    { id: 'basic', label: '기본정보', content: <BasicInfoTab library={library} /> },
    ...(library.kind === 'MAIN'
      ? [
          {
            id: 'branches',
            label: '분관',
            content: <BranchSection parentId={library.id} />,
          },
        ]
      : []),
  ];

  return (
    <>
      <PageHeader
        title={
          <span className="inline-flex items-center gap-3">
            {library.name}
            <StatusBadge status={library.status} />
            <Badge tone="neutral" variant="soft" size="sm">{library.code}</Badge>
          </span>
        }
        description={library.address ?? ''}
        breadcrumb={breadcrumb}
        actions={
          canWrite ? (
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                leftIcon={<Icon as={Pencil} size="sm" />}
                onClick={() => setEditOpen(true)}
              >
                수정
              </Button>
              <Button
                variant="danger"
                leftIcon={<Icon as={Trash2} size="sm" />}
                onClick={() => setConfirmDelete(true)}
              >
                삭제
              </Button>
            </div>
          ) : undefined
        }
      />

      <div className="p-6">
        <Tabs items={tabItems} defaultValue="basic" />
      </div>

      <FormModal
        open={editOpen}
        title="도서관 정보 수정"
        submitText="저장"
        submitting={updateMutation.isPending}
        onClose={() => setEditOpen(false)}
        onSubmit={() => formRef.current?.submit()}
      >
        <LibraryForm
          ref={formRef}
          initial={library}
          onValid={(values) => {
            updateMutation.mutate(
              { id: library.id, input: values as UpdateLibraryInput },
              {
                onSuccess: () => {
                  show({ type: 'success', title: '도서관 정보가 수정되었습니다.' });
                  setEditOpen(false);
                },
                onError: (e) =>
                  show({
                    type: 'danger',
                    title: '수정 실패',
                    description: e.userMessage ?? e.message,
                  }),
              },
            );
          }}
        />
      </FormModal>

      <ConfirmDialog
        open={confirmDelete}
        title="도서관을 삭제하시겠습니까?"
        description="소속 회원·소장 자료가 있다면 삭제가 거부될 수 있습니다."
        confirmText="삭제"
        tone="danger"
        loading={deleteMutation.isPending}
        onConfirm={() => {
          setConfirmDelete(false);
          deleteMutation.mutate(library.id, {
            onSuccess: () => {
              show({ type: 'success', title: '도서관이 삭제되었습니다.' });
              router.push('/facility/libraries');
            },
            onError: (e) =>
              show({
                type: 'danger',
                title: '삭제 실패',
                description: e.userMessage ?? e.message,
              }),
          });
        }}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
}

function BasicInfoTab({ library }: { library: Library }) {
  const rows: Array<[string, string | undefined | null]> = [
    ['코드', library.code],
    ['이름', library.name],
    ['유형', kindLabel(library.kind)],
    ['주소', library.address],
    ['대표 전화', library.phone],
    ['대표 이메일', library.email],
    ['운영 시간', library.openHours],
    ['상위 본관', library.parentId ?? '—'],
    ['개관일', library.openedAt ?? '—'],
    ['등록일', formatDateTime(library.createdAt)],
  ];

  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
      {rows.map(([label, value]) => (
        <div key={label} className="flex border-b border-neutral-100 py-2">
          <dt className="w-28 shrink-0 text-[13px] text-neutral-500">{label}</dt>
          <dd className="text-[14px] text-neutral-900">{value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  );
}

function kindLabel(k: Library['kind']): string {
  switch (k) {
    case 'MAIN':
      return '본관';
    case 'BRANCH':
      return '분관';
    case 'BOOK_MOBILE':
      return '이동도서관';
    case 'PARTNER':
      return '협력기관';
  }
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('ko-KR');
  } catch {
    return iso;
  }
}
