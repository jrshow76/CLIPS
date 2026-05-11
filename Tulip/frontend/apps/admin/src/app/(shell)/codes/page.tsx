'use client';

/**
 * 코드 관리 (`/codes`)
 *
 * - 좌측: 코드 그룹 트리/리스트
 * - 우측: 선택된 그룹의 코드 값 테이블
 * - 글로벌 코드는 readonly, 테넌트 코드는 추가/수정/삭제 가능
 */
import {
  useCodeGroupsQuery,
  useCodeItemsQuery,
  useDeleteCodeItemMutation,
  useUpsertCodeItemMutation,
  type CodeGroup,
  type CodeItem,
  type UpsertCodeItemInput,
} from '@tulip/api-client';
import { useHasScope } from '@tulip/auth';
import {
  AccessDenied,
  Badge,
  Button,
  ConfirmDialog,
  DataTable,
  EmptyState,
  FormField,
  FormModal,
  Icon,
  Input,
  PageHeader,
  Skeleton,
  Spinner,
  StatusBadge,
  useToast,
  cn,
  type Column,
} from '@tulip/ui';
import { Lock, Plus, Tag } from 'lucide-react';
import { useState } from 'react';

export default function CodesPage() {
  const canRead = useHasScope('code:read');
  if (!canRead) {
    return (
      <>
        <PageHeader
          title="코드 관리"
          breadcrumb={[{ label: '홈', href: '/' }, { label: '코드 관리' }]}
        />
        <div className="p-6">
          <AccessDenied requiredScope="코드 조회(code:read)" />
        </div>
      </>
    );
  }
  return <CodesPageInner />;
}

function CodesPageInner() {
  const canWrite = useHasScope('code:write');
  const { show } = useToast();

  const groupsQuery = useCodeGroupsQuery();
  const groups = groupsQuery.data ?? [];
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const activeGroupCode = selectedGroup ?? groups[0]?.groupCode ?? null;
  const activeGroup = groups.find((g) => g.groupCode === activeGroupCode) ?? null;
  const itemsQuery = useCodeItemsQuery(activeGroupCode ?? undefined);

  const [editTarget, setEditTarget] = useState<CodeItem | 'NEW' | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CodeItem | null>(null);
  const upsertMutation = useUpsertCodeItemMutation();
  const deleteMutation = useDeleteCodeItemMutation();

  const isTenantGroup = activeGroup?.scope === 'TENANT';
  const canEdit = canWrite && isTenantGroup;

  const columns: Column<CodeItem>[] = [
    {
      id: 'code',
      header: '코드',
      cell: (i) => <span className="font-mono text-[13px] text-neutral-900">{i.code}</span>,
      width: 160,
    },
    { id: 'label', header: '라벨', cell: (i) => i.label },
    {
      id: 'ordinal',
      header: '순서',
      cell: (i) => i.ordinal ?? '—',
      align: 'right',
      width: 70,
    },
    {
      id: 'active',
      header: '활성',
      cell: (i) => <StatusBadge status={i.active ? 'ACTIVE' : 'INACTIVE'} />,
      width: 90,
    },
    {
      id: 'scope',
      header: 'Scope',
      cell: (i) =>
        i.scope === 'GLOBAL' ? (
          <Badge tone="neutral" variant="outline" size="sm">
            <Icon as={Lock} size="xs" /> 글로벌
          </Badge>
        ) : (
          <Badge tone="primary" variant="soft" size="sm">테넌트</Badge>
        ),
      width: 110,
    },
    {
      id: 'actions',
      header: <span className="sr-only">작업</span>,
      cell: (i) =>
        canEdit && i.scope === 'TENANT' ? (
          <div className="flex justify-end gap-2 text-[12px]">
            <button
              type="button"
              className="text-primary-600 hover:underline"
              onClick={() => setEditTarget(i)}
            >
              수정
            </button>
            <button
              type="button"
              className="text-danger hover:underline"
              onClick={() => setDeleteTarget(i)}
            >
              삭제
            </button>
          </div>
        ) : (
          <span className="text-[12px] text-neutral-400">읽기전용</span>
        ),
      align: 'right',
      width: 130,
    },
  ];

  return (
    <>
      <PageHeader
        title="코드 관리"
        description="시스템 공통 코드(글로벌)와 테넌트 전용 코드를 조회/관리합니다."
        breadcrumb={[{ label: '홈', href: '/' }, { label: '코드 관리' }]}
        actions={
          canEdit && activeGroupCode ? (
            <Button
              variant="primary"
              leftIcon={<Icon as={Plus} size="sm" />}
              onClick={() => setEditTarget('NEW')}
            >
              코드 추가
            </Button>
          ) : undefined
        }
      />

      <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-[260px_1fr]">
        {/* 좌측: 그룹 리스트 */}
        <aside className="rounded-lg border border-neutral-200 bg-surface-card">
          <header className="border-b border-neutral-200 px-3 py-2 text-overline text-neutral-600">
            코드 그룹
          </header>
          {groupsQuery.isLoading ? (
            <div className="flex flex-col gap-2 p-3">
              <Skeleton height={28} />
              <Skeleton height={28} />
              <Skeleton height={28} />
            </div>
          ) : groups.length === 0 ? (
            <EmptyState
              icon={<Icon as={Tag} size="lg" />}
              title="등록된 코드 그룹이 없습니다"
            />
          ) : (
            <ul role="list" className="flex flex-col py-1">
              {groups.map((g) => (
                <li key={g.groupCode}>
                  <button
                    type="button"
                    onClick={() => setSelectedGroup(g.groupCode)}
                    className={cn(
                      'flex w-full items-center gap-2 px-3 py-2 text-left text-[13px]',
                      'transition-colors focus-visible:outline-none focus-visible:shadow-focus',
                      g.groupCode === activeGroupCode
                        ? 'bg-primary-50 text-primary-700 font-semibold'
                        : 'text-neutral-700 hover:bg-neutral-100',
                    )}
                  >
                    <span className="flex-1 truncate">{g.groupName}</span>
                    <ScopeChip group={g} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        {/* 우측: 코드 값 */}
        <section className="flex flex-col gap-3">
          {activeGroup ? (
            <header className="flex items-center gap-3">
              <h2 className="text-h3 text-neutral-900">{activeGroup.groupName}</h2>
              <code className="rounded bg-neutral-100 px-2 py-0.5 font-mono text-[12px] text-neutral-700">
                {activeGroup.groupCode}
              </code>
              <ScopeChip group={activeGroup} />
              {activeGroup.description && (
                <span className="text-[12px] text-neutral-500">{activeGroup.description}</span>
              )}
            </header>
          ) : (
            <span className="text-[13px] text-neutral-500">코드 그룹을 선택하세요.</span>
          )}

          {itemsQuery.isLoading ? (
            <div className="flex items-center gap-2 py-6 text-neutral-500">
              <Spinner size="sm" /> 불러오는 중…
            </div>
          ) : itemsQuery.isError ? (
            <div className="rounded-lg border border-danger bg-danger-50 px-4 py-3 text-[13px] text-danger">
              코드 항목을 불러오지 못했습니다 ({itemsQuery.error?.code ?? 'ERR'}).
            </div>
          ) : (
            <DataTable<CodeItem>
              columns={columns}
              data={itemsQuery.data ?? []}
              rowKey={(i) => `${i.groupCode}/${i.code}`}
              density="compact"
              empty={
                <EmptyState
                  icon={<Icon as={Tag} size="xl" />}
                  title="등록된 코드가 없습니다"
                  description={
                    canEdit
                      ? '우측 상단의 “코드 추가” 버튼으로 새 코드를 등록하세요.'
                      : '글로벌 코드는 플랫폼 관리자만 추가/수정할 수 있습니다.'
                  }
                />
              }
            />
          )}
        </section>
      </div>

      <FormModal
        open={editTarget !== null}
        title={editTarget === 'NEW' ? '코드 추가' : '코드 수정'}
        submitText="저장"
        submitting={upsertMutation.isPending}
        onClose={() => setEditTarget(null)}
        onSubmit={(e) => {
          const form = e.currentTarget;
          const fd = new FormData(form);
          const input: UpsertCodeItemInput = {
            code: String(fd.get('code') ?? '').trim(),
            label: String(fd.get('label') ?? '').trim(),
            ordinal: Number(fd.get('ordinal') || '0') || undefined,
            active: fd.get('active') === 'on',
          };
          if (!input.code || !input.label || !activeGroupCode) return;
          upsertMutation.mutate(
            {
              groupCode: activeGroupCode,
              input,
              mode: editTarget === 'NEW' ? 'create' : 'update',
            },
            {
              onSuccess: () => {
                show({
                  type: 'success',
                  title: editTarget === 'NEW' ? '코드가 추가되었습니다.' : '코드가 수정되었습니다.',
                });
                setEditTarget(null);
              },
              onError: (err) =>
                show({
                  type: 'danger',
                  title: '저장 실패',
                  description: err.userMessage ?? err.message,
                }),
            },
          );
        }}
      >
        <CodeItemFields target={editTarget} />
      </FormModal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="코드를 삭제하시겠습니까?"
        description={
          deleteTarget
            ? `${deleteTarget.label} (${deleteTarget.code}) 코드가 삭제됩니다.`
            : ''
        }
        confirmText="삭제"
        tone="danger"
        loading={deleteMutation.isPending}
        onConfirm={() => {
          if (!deleteTarget) return;
          deleteMutation.mutate(
            { groupCode: deleteTarget.groupCode, code: deleteTarget.code },
            {
              onSuccess: () => {
                show({ type: 'success', title: '코드가 삭제되었습니다.' });
                setDeleteTarget(null);
              },
              onError: (err) =>
                show({
                  type: 'danger',
                  title: '삭제 실패',
                  description: err.userMessage ?? err.message,
                }),
            },
          );
        }}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}

function CodeItemFields({ target }: { target: CodeItem | 'NEW' | null }) {
  const initial = target && target !== 'NEW' ? target : undefined;
  return (
    <>
      <FormField label="코드" required>
        {(p) => (
          <Input
            {...p}
            name="code"
            defaultValue={initial?.code ?? ''}
            placeholder="EVENT, EMERGENCY 등"
            disabled={!!initial}
          />
        )}
      </FormField>
      <FormField label="라벨" required>
        {(p) => (
          <Input
            {...p}
            name="label"
            defaultValue={initial?.label ?? ''}
            placeholder="화면에 표시될 한글명"
          />
        )}
      </FormField>
      <div className="grid grid-cols-2 gap-4">
        <FormField label="정렬 순서">
          {(p) => (
            <Input
              {...p}
              name="ordinal"
              type="number"
              min={0}
              defaultValue={initial?.ordinal ?? ''}
            />
          )}
        </FormField>
        <FormField label="활성">
          {() => (
            <label className="inline-flex h-10 items-center gap-2 text-[13px] text-neutral-700">
              <input
                type="checkbox"
                name="active"
                defaultChecked={initial?.active ?? true}
                className="rounded border-neutral-300 text-primary-500 focus-visible:shadow-focus"
              />
              사용 가능
            </label>
          )}
        </FormField>
      </div>
    </>
  );
}

function ScopeChip({ group }: { group: CodeGroup }) {
  if (group.scope === 'GLOBAL') {
    return (
      <Badge tone="neutral" variant="outline" size="sm">
        <Icon as={Lock} size="xs" /> 글로벌
      </Badge>
    );
  }
  return (
    <Badge tone="primary" variant="soft" size="sm">
      테넌트
    </Badge>
  );
}
