'use client';

/**
 * MemberCardSection — 회원 상세 페이지의 "카드" 탭 본문.
 *
 * - 카드 목록 표시
 * - "카드 발급" 버튼 → ConfirmDialog로 발급 확정
 */
import {
  useIssueMemberCardMutation,
  useMemberCardsQuery,
  type MemberCard,
} from '@tulip/api-client';
import {
  Button,
  ConfirmDialog,
  DataTable,
  EmptyState,
  Icon,
  StatusBadge,
  Spinner,
  useToast,
  type Column,
} from '@tulip/ui';
import { CreditCard } from 'lucide-react';
import { useState } from 'react';

export interface MemberCardSectionProps {
  memberId: string;
}

export function MemberCardSection({ memberId }: MemberCardSectionProps) {
  const { show } = useToast();
  const { data, isLoading } = useMemberCardsQuery(memberId);
  const issueMutation = useIssueMemberCardMutation();

  const [confirmOpen, setConfirmOpen] = useState(false);

  function handleIssue() {
    setConfirmOpen(false);
    issueMutation.mutate(
      { memberId, input: { type: 'BARCODE' } },
      {
        onSuccess: () => show({ type: 'success', title: '카드가 발급되었습니다.' }),
        onError: (e) =>
          show({
            type: 'danger',
            title: '카드 발급 실패',
            description: e.userMessage ?? e.message,
          }),
      },
    );
  }

  const columns: Column<MemberCard>[] = [
    { id: 'cardNumber', header: '카드번호', cell: (row) => row.cardNumber, width: 200 },
    {
      id: 'type',
      header: '유형',
      cell: (row) => (
        <span className="text-neutral-700">{cardTypeLabel(row.type)}</span>
      ),
      width: 100,
    },
    {
      id: 'issuedAt',
      header: '발급일',
      cell: (row) => formatDate(row.issuedAt),
      width: 140,
    },
    {
      id: 'expiresAt',
      header: '만료일',
      cell: (row) => (row.expiresAt ? formatDate(row.expiresAt) : '—'),
      width: 140,
    },
    {
      id: 'status',
      header: '상태',
      cell: (row) =>
        row.revokedAt ? (
          <StatusBadge status="WITHDRAWN" />
        ) : (
          <StatusBadge status="ACTIVE" />
        ),
      width: 100,
    },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-2 py-6 text-neutral-500">
        <Spinner size="sm" /> 카드 정보를 불러오는 중…
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-h3 text-neutral-900">발급 카드</h3>
        <Button
          size="sm"
          variant="primary"
          leftIcon={<Icon as={CreditCard} size="sm" />}
          onClick={() => setConfirmOpen(true)}
          loading={issueMutation.isPending}
        >
          카드 발급
        </Button>
      </div>

      {(data?.length ?? 0) === 0 ? (
        <EmptyState
          icon={<Icon as={CreditCard} size="xl" />}
          title="발급된 카드가 없습니다"
          description="회원에게 새 회원증을 발급할 수 있습니다."
        />
      ) : (
        <DataTable<MemberCard>
          columns={columns}
          data={data ?? []}
          rowKey={(r) => r.id}
          density="compact"
        />
      )}

      <ConfirmDialog
        open={confirmOpen}
        title="회원증을 발급하시겠습니까?"
        description="신규 바코드 회원증이 즉시 발급됩니다."
        confirmText="발급"
        loading={issueMutation.isPending}
        onConfirm={handleIssue}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}

function cardTypeLabel(t: MemberCard['type']): string {
  switch (t) {
    case 'BARCODE':
      return '바코드';
    case 'RFID':
      return 'RFID';
    case 'MOBILE':
      return '모바일';
    default:
      return '—';
  }
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('ko-KR');
  } catch {
    return iso;
  }
}
