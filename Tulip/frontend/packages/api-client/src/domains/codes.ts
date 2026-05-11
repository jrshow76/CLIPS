/**
 * code-policy-service 코드 도메인 모듈
 *
 * 가정 API:
 *   GET /api/v1/codes/groups
 *   GET /api/v1/codes/groups/{groupCode}/items
 *   POST /api/v1/codes/groups/{groupCode}/items (테넌트 코드)
 *   PATCH /api/v1/codes/groups/{groupCode}/items/{code}
 *   DELETE /api/v1/codes/groups/{groupCode}/items/{code}
 *
 * 글로벌 코드는 readonly, 테넌트 코드는 CRUD 가능.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
} from '@tanstack/react-query';

import { useApiClient } from '../context';
import type { ApiError } from '../errors';
import { isMockMode, mockDelay } from '../mock';

// ───────────────────────────── 타입 ─────────────────────────────

export type CodeScope = 'GLOBAL' | 'TENANT';

export interface CodeGroup {
  /** 그룹 코드 (예: MEMBER_TYPE, LOAN_STATUS) */
  groupCode: string;
  /** 그룹 이름 */
  groupName: string;
  scope: CodeScope;
  description?: string;
  /** 항목 수 (요약) */
  itemCount?: number;
}

export interface CodeItem {
  groupCode: string;
  code: string;
  label: string;
  /** 정렬 순서 */
  ordinal?: number;
  /** 사용 가능 여부 */
  active: boolean;
  /** 부가 속성 (JSON) */
  attributes?: Record<string, unknown>;
  /** scope === GLOBAL 이면 readonly */
  scope: CodeScope;
}

export interface UpsertCodeItemInput {
  code: string;
  label: string;
  ordinal?: number;
  active?: boolean;
  attributes?: Record<string, unknown>;
}

// ───────────────────────────── Query Keys ─────────────────────────────

export const codeKeys = {
  all: ['codes'] as const,
  groups: () => [...codeKeys.all, 'groups'] as const,
  items: (groupCode: string) => [...codeKeys.all, 'items', groupCode] as const,
};

// ───────────────────────────── Mock ─────────────────────────────

const MOCK_GROUPS: CodeGroup[] = [
  { groupCode: 'MEMBER_TYPE', groupName: '회원 유형', scope: 'GLOBAL', itemCount: 5 },
  { groupCode: 'MEMBER_STATUS', groupName: '회원 상태', scope: 'GLOBAL', itemCount: 4 },
  { groupCode: 'LIBRARY_KIND', groupName: '도서관 유형', scope: 'GLOBAL', itemCount: 4 },
  { groupCode: 'LOAN_STATUS', groupName: '대출 상태', scope: 'GLOBAL', itemCount: 5 },
  {
    groupCode: 'TENANT_NOTICE_KIND',
    groupName: '테넌트 공지 유형',
    scope: 'TENANT',
    itemCount: 3,
    description: '본 테넌트에서 사용하는 공지사항 분류',
  },
];

const MOCK_ITEMS: Record<string, CodeItem[]> = {
  MEMBER_TYPE: [
    { groupCode: 'MEMBER_TYPE', code: 'ADULT', label: '성인', ordinal: 1, active: true, scope: 'GLOBAL' },
    { groupCode: 'MEMBER_TYPE', code: 'YOUTH', label: '청소년', ordinal: 2, active: true, scope: 'GLOBAL' },
    { groupCode: 'MEMBER_TYPE', code: 'CHILD', label: '어린이', ordinal: 3, active: true, scope: 'GLOBAL' },
    { groupCode: 'MEMBER_TYPE', code: 'STAFF', label: '직원', ordinal: 4, active: true, scope: 'GLOBAL' },
    { groupCode: 'MEMBER_TYPE', code: 'GUEST', label: '게스트', ordinal: 5, active: false, scope: 'GLOBAL' },
  ],
  MEMBER_STATUS: [
    { groupCode: 'MEMBER_STATUS', code: 'ACTIVE', label: '정상', ordinal: 1, active: true, scope: 'GLOBAL' },
    { groupCode: 'MEMBER_STATUS', code: 'SUSPENDED', label: '정지', ordinal: 2, active: true, scope: 'GLOBAL' },
    { groupCode: 'MEMBER_STATUS', code: 'EXPIRED', label: '만료', ordinal: 3, active: true, scope: 'GLOBAL' },
    { groupCode: 'MEMBER_STATUS', code: 'WITHDRAWN', label: '탈퇴', ordinal: 4, active: true, scope: 'GLOBAL' },
  ],
  LIBRARY_KIND: [
    { groupCode: 'LIBRARY_KIND', code: 'MAIN', label: '본관', ordinal: 1, active: true, scope: 'GLOBAL' },
    { groupCode: 'LIBRARY_KIND', code: 'BRANCH', label: '분관', ordinal: 2, active: true, scope: 'GLOBAL' },
    { groupCode: 'LIBRARY_KIND', code: 'BOOK_MOBILE', label: '이동도서관', ordinal: 3, active: true, scope: 'GLOBAL' },
    { groupCode: 'LIBRARY_KIND', code: 'PARTNER', label: '협력기관', ordinal: 4, active: true, scope: 'GLOBAL' },
  ],
  LOAN_STATUS: [
    { groupCode: 'LOAN_STATUS', code: 'ON_LOAN', label: '대출중', ordinal: 1, active: true, scope: 'GLOBAL' },
    { groupCode: 'LOAN_STATUS', code: 'RETURNED', label: '반납완료', ordinal: 2, active: true, scope: 'GLOBAL' },
    { groupCode: 'LOAN_STATUS', code: 'OVERDUE', label: '연체', ordinal: 3, active: true, scope: 'GLOBAL' },
    { groupCode: 'LOAN_STATUS', code: 'LOST', label: '분실', ordinal: 4, active: true, scope: 'GLOBAL' },
    { groupCode: 'LOAN_STATUS', code: 'RENEWED', label: '연장', ordinal: 5, active: true, scope: 'GLOBAL' },
  ],
  TENANT_NOTICE_KIND: [
    { groupCode: 'TENANT_NOTICE_KIND', code: 'GENERAL', label: '일반', ordinal: 1, active: true, scope: 'TENANT' },
    { groupCode: 'TENANT_NOTICE_KIND', code: 'EVENT', label: '행사', ordinal: 2, active: true, scope: 'TENANT' },
    { groupCode: 'TENANT_NOTICE_KIND', code: 'EMERGENCY', label: '긴급', ordinal: 3, active: true, scope: 'TENANT' },
  ],
};

// ───────────────────────────── Hooks ─────────────────────────────

export function useCodeGroupsQuery() {
  const client = useApiClient();
  return useQuery<CodeGroup[], ApiError>({
    queryKey: codeKeys.groups(),
    queryFn: () => {
      if (isMockMode()) return mockDelay(MOCK_GROUPS);
      return client.get<CodeGroup[]>('/codes/groups');
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useCodeItemsQuery(groupCode: string | undefined) {
  const client = useApiClient();
  return useQuery<CodeItem[], ApiError>({
    queryKey: codeKeys.items(groupCode ?? '__none__'),
    enabled: !!groupCode,
    queryFn: () => {
      if (isMockMode()) return mockDelay(MOCK_ITEMS[groupCode!] ?? []);
      return client.get<CodeItem[]>(`/codes/groups/${groupCode}/items`);
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpsertCodeItemMutation(
  options?: UseMutationOptions<
    CodeItem,
    ApiError,
    { groupCode: string; input: UpsertCodeItemInput; mode: 'create' | 'update' }
  >,
) {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation<
    CodeItem,
    ApiError,
    { groupCode: string; input: UpsertCodeItemInput; mode: 'create' | 'update' }
  >({
    mutationFn: ({ groupCode, input, mode }) => {
      if (isMockMode()) {
        const list = MOCK_ITEMS[groupCode] ?? [];
        if (mode === 'create') {
          const item: CodeItem = {
            groupCode,
            code: input.code,
            label: input.label,
            ordinal: input.ordinal ?? list.length + 1,
            active: input.active ?? true,
            attributes: input.attributes,
            scope: 'TENANT',
          };
          MOCK_ITEMS[groupCode] = [...list, item];
          return mockDelay(item);
        }
        const idx = list.findIndex((x) => x.code === input.code);
        if (idx < 0) return Promise.reject(new Error('not found'));
        list[idx] = { ...list[idx], ...input };
        return mockDelay(list[idx]);
      }
      return mode === 'create'
        ? client.post<CodeItem>(`/codes/groups/${groupCode}/items`, input)
        : client.patch<CodeItem>(`/codes/groups/${groupCode}/items/${input.code}`, input);
    },
    onSuccess: (data, vars, _onMutate, mctx) => {
      void qc.invalidateQueries({ queryKey: codeKeys.items(vars.groupCode) });
      return options?.onSuccess?.(data, vars, _onMutate, mctx);
    },
    ...options,
  });
}

export function useDeleteCodeItemMutation(
  options?: UseMutationOptions<void, ApiError, { groupCode: string; code: string }>,
) {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation<void, ApiError, { groupCode: string; code: string }>({
    mutationFn: ({ groupCode, code }) => {
      if (isMockMode()) {
        const list = MOCK_ITEMS[groupCode] ?? [];
        MOCK_ITEMS[groupCode] = list.filter((x) => x.code !== code);
        return mockDelay(undefined);
      }
      return client.delete<void>(`/codes/groups/${groupCode}/items/${code}`);
    },
    onSuccess: (data, vars, _onMutate, mctx) => {
      void qc.invalidateQueries({ queryKey: codeKeys.items(vars.groupCode) });
      return options?.onSuccess?.(data, vars, _onMutate, mctx);
    },
    ...options,
  });
}
