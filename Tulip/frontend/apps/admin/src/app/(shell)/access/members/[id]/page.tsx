'use client';

/**
 * 회원 상세 페이지 (`/access/members/{id}`)
 *
 * - 탭: 기본정보 · 카드 · 동의(placeholder) · 활동(placeholder)
 * - 액션: 정보 수정, 정지/복원, 삭제(soft)
 */
import {
  useDeleteMemberMutation,
  useMemberQuery,
  useUpdateMemberMutation,
  type Member,
  type MemberStatus,
  type UpdateMemberInput,
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
import { ArrowLeft, ShieldOff, ShieldCheck, Trash2, Pencil } from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useMemo, useRef, useState } from 'react';

import { MemberCardSection } from '../_components/MemberCardSection';
import { MemberForm, type MemberFormHandle } from '../_components/MemberForm';

export default function MemberDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const canRead = useHasScope('member:read');
  const canWrite = useHasScope('member:write');
  const router = useRouter();
  const { show } = useToast();

  const memberQuery = useMemberQuery(id);
  const updateMutation = useUpdateMemberMutation();
  const deleteMutation = useDeleteMemberMutation();

  const [editOpen, setEditOpen] = useState(false);
  const [confirmStatus, setConfirmStatus] = useState<MemberStatus | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const formRef = useRef<MemberFormHandle>(null);

  const member = memberQuery.data;

  const breadcrumb = useMemo(
    () => [
      { label: '홈', href: '/' },
      { label: '회원/이용', href: '/access/members' },
      { label: '회원 관리', href: '/access/members' },
      { label: member?.name ?? '상세' },
    ],
    [member?.name],
  );

  if (!canRead) {
    return (
      <>
        <PageHeader title="회원 상세" breadcrumb={breadcrumb} />
        <div className="p-6">
          <AccessDenied requiredScope="회원 조회(member:read)" />
        </div>
      </>
    );
  }

  if (memberQuery.isLoading) {
    return (
      <>
        <PageHeader title="회원 상세" breadcrumb={breadcrumb} />
        <div className="flex flex-col gap-3 p-6">
          <Skeleton height={32} width={240} />
          <Skeleton height={20} width={360} />
          <Skeleton height={300} />
        </div>
      </>
    );
  }

  if (memberQuery.isError || !member) {
    return (
      <>
        <PageHeader title="회원 상세" breadcrumb={breadcrumb} />
        <div className="p-6">
          <EmptyState
            title="회원 정보를 찾을 수 없습니다"
            description="회원이 삭제되었거나 접근 권한이 없습니다."
            primaryAction={
              <Button
                variant="secondary"
                leftIcon={<Icon as={ArrowLeft} size="sm" />}
                onClick={() => router.push('/access/members')}
              >
                목록으로
              </Button>
            }
          />
        </div>
      </>
    );
  }

  function handleStatusChange(next: MemberStatus) {
    if (!member) return;
    setConfirmStatus(null);
    updateMutation.mutate(
      { id: member.id, input: { status: next } },
      {
        onSuccess: () =>
          show({
            type: 'success',
            title:
              next === 'SUSPENDED'
                ? '회원이 정지되었습니다.'
                : next === 'ACTIVE'
                  ? '회원이 복원되었습니다.'
                  : '회원 상태가 변경되었습니다.',
          }),
        onError: (e) =>
          show({
            type: 'danger',
            title: '상태 변경 실패',
            description: e.userMessage ?? e.message,
          }),
      },
    );
  }

  function handleDelete() {
    if (!member) return;
    setConfirmDelete(false);
    deleteMutation.mutate(member.id, {
      onSuccess: () => {
        show({ type: 'success', title: '회원이 삭제되었습니다.' });
        router.push('/access/members');
      },
      onError: (e) =>
        show({
          type: 'danger',
          title: '삭제 실패',
          description: e.userMessage ?? e.message,
        }),
    });
  }

  const tabItems = [
    {
      id: 'basic',
      label: '기본정보',
      content: <BasicInfoTab member={member} />,
    },
    {
      id: 'cards',
      label: '카드',
      content: <MemberCardSection memberId={member.id} />,
    },
    {
      id: 'agreements',
      label: '동의',
      content: (
        <EmptyState
          title="개인정보 동의 내역 (준비 중)"
          description="Phase 2에서 약관·개인정보 동의 이력을 노출합니다."
        />
      ),
    },
    {
      id: 'activity',
      label: '활동',
      content: (
        <EmptyState
          title="활동 이력 (준비 중)"
          description="대출·예약·연체 이력을 본 탭에서 통합 조회할 예정입니다."
        />
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title={
          <span className="inline-flex items-center gap-3">
            {member.name}
            <StatusBadge status={member.status} />
            <Badge tone="neutral" variant="soft" size="sm">
              {member.memberNumber}
            </Badge>
          </span>
        }
        description={member.libraryName ?? member.libraryId}
        breadcrumb={breadcrumb}
        actions={
          canWrite ? (
            <div className="flex items-center gap-2">
              {member.status === 'ACTIVE' ? (
                <Button
                  variant="secondary"
                  leftIcon={<Icon as={ShieldOff} size="sm" />}
                  onClick={() => setConfirmStatus('SUSPENDED')}
                >
                  정지
                </Button>
              ) : (
                <Button
                  variant="secondary"
                  leftIcon={<Icon as={ShieldCheck} size="sm" />}
                  onClick={() => setConfirmStatus('ACTIVE')}
                >
                  복원
                </Button>
              )}
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
          ) : (
            <Link href="/access/members" className="text-[13px] text-primary-600 hover:underline">
              목록으로
            </Link>
          )
        }
      />

      <div className="p-6">
        <Tabs items={tabItems} defaultValue="basic" />
      </div>

      <FormModal
        open={editOpen}
        title="회원 정보 수정"
        submitText="저장"
        submitting={updateMutation.isPending}
        onClose={() => setEditOpen(false)}
        onSubmit={() => formRef.current?.submit()}
      >
        <MemberForm
          ref={formRef}
          initial={member}
          onValid={(values) => {
            updateMutation.mutate(
              { id: member.id, input: values as UpdateMemberInput },
              {
                onSuccess: () => {
                  show({ type: 'success', title: '회원 정보가 수정되었습니다.' });
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
        open={confirmStatus !== null}
        title={
          confirmStatus === 'SUSPENDED'
            ? '회원을 정지하시겠습니까?'
            : '회원을 복원하시겠습니까?'
        }
        description={
          confirmStatus === 'SUSPENDED'
            ? '정지된 회원은 대출·예약 등 모든 서비스 이용이 제한됩니다.'
            : '복원 후 해당 회원은 다시 정상 이용이 가능합니다.'
        }
        confirmText={confirmStatus === 'SUSPENDED' ? '정지' : '복원'}
        tone={confirmStatus === 'SUSPENDED' ? 'danger' : 'primary'}
        loading={updateMutation.isPending}
        onConfirm={() => confirmStatus && handleStatusChange(confirmStatus)}
        onCancel={() => setConfirmStatus(null)}
      />

      <ConfirmDialog
        open={confirmDelete}
        title="회원을 삭제하시겠습니까?"
        description="삭제 후에는 복구할 수 없습니다. 정말 진행하시겠습니까?"
        confirmText="삭제"
        tone="danger"
        loading={deleteMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
}

function BasicInfoTab({ member }: { member: Member }) {
  const rows: Array<[string, string | undefined | null]> = [
    ['회원번호', member.memberNumber],
    ['이름', member.name],
    ['이메일', member.email],
    ['연락처', member.phone],
    ['생년월일', member.birthDate],
    ['소속 도서관', member.libraryName ?? member.libraryId],
    ['가입일', formatDateTime(member.joinedAt)],
    ['만료일', member.expiresAt ? formatDateTime(member.expiresAt) : '—'],
    ['상태 사유', member.statusReason],
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

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('ko-KR');
  } catch {
    return iso;
  }
}
