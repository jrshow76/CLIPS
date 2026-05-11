/**
 * member-service 도메인 모듈
 *
 * 가정 API:
 *   GET    /api/v1/members?q&status&libraryId&memberType&page&size
 *   POST   /api/v1/members
 *   GET    /api/v1/members/{id}
 *   PATCH  /api/v1/members/{id}
 *   DELETE /api/v1/members/{id}
 *   POST   /api/v1/members/{id}/cards
 *   GET    /api/v1/members/{id}/cards
 *
 * 실제 백엔드 명세 확정 후 타입을 보강한다.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
  type UseQueryOptions,
} from '@tanstack/react-query';

import { useApiClient } from '../context';
import type { ApiError } from '../errors';
import { isMockMode, mockDelay } from '../mock';

import { compactQuery, type FlatOffsetPage } from './common';

// ───────────────────────────── 타입 ─────────────────────────────

export type MemberStatus = 'ACTIVE' | 'SUSPENDED' | 'EXPIRED' | 'WITHDRAWN';

export type MemberType = 'ADULT' | 'YOUTH' | 'CHILD' | 'STAFF' | 'GUEST';

export interface Member {
  id: string;
  /** 회원번호 (사람이 읽는 식별자) */
  memberNumber: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  birthDate?: string | null;
  memberType: MemberType;
  status: MemberStatus;
  libraryId: string;
  libraryName?: string;
  joinedAt: string;
  expiresAt?: string | null;
  /** 정지/만료 사유 */
  statusReason?: string | null;
  tags?: string[];
}

export interface MemberCard {
  id: string;
  memberId: string;
  /** 바코드/RFID 값 */
  cardNumber: string;
  issuedAt: string;
  expiresAt?: string | null;
  revokedAt?: string | null;
  type?: 'BARCODE' | 'RFID' | 'MOBILE';
}

export interface MemberListQuery {
  q?: string;
  status?: MemberStatus;
  libraryId?: string;
  memberType?: MemberType;
  page?: number;
  size?: number;
}

export interface CreateMemberInput {
  name: string;
  email?: string;
  phone?: string;
  birthDate?: string;
  memberType: MemberType;
  libraryId: string;
}

export interface UpdateMemberInput {
  name?: string;
  email?: string | null;
  phone?: string | null;
  birthDate?: string | null;
  memberType?: MemberType;
  libraryId?: string;
  status?: MemberStatus;
  statusReason?: string | null;
}

export interface IssueCardInput {
  cardNumber?: string;
  type?: MemberCard['type'];
  expiresAt?: string;
}

// ───────────────────────────── Query Keys ─────────────────────────────

export const memberKeys = {
  all: ['members'] as const,
  lists: () => [...memberKeys.all, 'list'] as const,
  list: (q: MemberListQuery) => [...memberKeys.lists(), q] as const,
  details: () => [...memberKeys.all, 'detail'] as const,
  detail: (id: string) => [...memberKeys.details(), id] as const,
  cards: (id: string) => [...memberKeys.detail(id), 'cards'] as const,
};

// ───────────────────────────── Mock 데이터 ─────────────────────────────

const MOCK_MEMBERS: Member[] = [
  {
    id: 'mbr_001',
    memberNumber: 'M2024-0001',
    name: '홍길동',
    email: 'hong@example.com',
    phone: '010-1234-5678',
    birthDate: '1985-03-12',
    memberType: 'ADULT',
    status: 'ACTIVE',
    libraryId: 'lib_main',
    libraryName: '중앙도서관',
    joinedAt: '2024-03-12T09:00:00+09:00',
    expiresAt: '2027-03-12T00:00:00+09:00',
  },
  {
    id: 'mbr_002',
    memberNumber: 'M2024-0002',
    name: '김영희',
    email: 'kim@example.com',
    phone: '010-2222-3333',
    birthDate: '2010-08-22',
    memberType: 'YOUTH',
    status: 'SUSPENDED',
    statusReason: '연체 도서 3건',
    libraryId: 'lib_branch1',
    libraryName: '분관A',
    joinedAt: '2023-09-01T10:00:00+09:00',
  },
  {
    id: 'mbr_003',
    memberNumber: 'M2025-0003',
    name: '박철수',
    phone: '010-7777-8888',
    memberType: 'ADULT',
    status: 'ACTIVE',
    libraryId: 'lib_main',
    libraryName: '중앙도서관',
    joinedAt: '2025-01-15T11:00:00+09:00',
  },
];

const MOCK_CARDS: MemberCard[] = [
  {
    id: 'crd_001',
    memberId: 'mbr_001',
    cardNumber: '9000000000001',
    issuedAt: '2024-03-12T09:00:00+09:00',
    expiresAt: '2027-03-12T00:00:00+09:00',
    type: 'BARCODE',
  },
];

function filterMockMembers(q: MemberListQuery): FlatOffsetPage<Member> {
  let items = [...MOCK_MEMBERS];
  if (q.q) {
    const kw = q.q.toLowerCase();
    items = items.filter(
      (m) =>
        m.name.toLowerCase().includes(kw) ||
        m.memberNumber.toLowerCase().includes(kw) ||
        (m.phone ?? '').includes(kw),
    );
  }
  if (q.status) items = items.filter((m) => m.status === q.status);
  if (q.libraryId) items = items.filter((m) => m.libraryId === q.libraryId);
  if (q.memberType) items = items.filter((m) => m.memberType === q.memberType);
  const page = q.page ?? 1;
  const size = q.size ?? 20;
  const total = items.length;
  const start = (page - 1) * size;
  return { items: items.slice(start, start + size), page, size, total };
}

// ───────────────────────────── Hooks ─────────────────────────────

export function useMembersQuery(
  params: MemberListQuery,
  options?: Omit<UseQueryOptions<FlatOffsetPage<Member>, ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<FlatOffsetPage<Member>, ApiError>({
    queryKey: memberKeys.list(params),
    queryFn: () => {
      if (isMockMode()) return mockDelay(filterMockMembers(params));
      return client.get<FlatOffsetPage<Member>>('/members', { query: compactQuery(params) });
    },
    placeholderData: (prev) => prev,
    ...options,
  });
}

export function useMemberQuery(
  id: string | undefined,
  options?: Omit<UseQueryOptions<Member, ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<Member, ApiError>({
    queryKey: memberKeys.detail(id ?? '__none__'),
    enabled: !!id,
    queryFn: () => {
      if (isMockMode()) {
        const m = MOCK_MEMBERS.find((x) => x.id === id);
        if (!m) return Promise.reject(new Error('not found'));
        return mockDelay(m);
      }
      return client.get<Member>(`/members/${id}`);
    },
    ...options,
  });
}

export function useMemberCardsQuery(memberId: string | undefined) {
  const client = useApiClient();
  return useQuery<MemberCard[], ApiError>({
    queryKey: memberKeys.cards(memberId ?? '__none__'),
    enabled: !!memberId,
    queryFn: () => {
      if (isMockMode()) {
        return mockDelay(MOCK_CARDS.filter((c) => c.memberId === memberId));
      }
      return client.get<MemberCard[]>(`/members/${memberId}/cards`);
    },
  });
}

export function useCreateMemberMutation(
  options?: UseMutationOptions<Member, ApiError, CreateMemberInput>,
) {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation<Member, ApiError, CreateMemberInput>({
    mutationFn: (input) => {
      if (isMockMode()) {
        const m: Member = {
          id: `mbr_${Date.now()}`,
          memberNumber: `M${new Date().getFullYear()}-${String(MOCK_MEMBERS.length + 1).padStart(
            4,
            '0',
          )}`,
          name: input.name,
          email: input.email ?? null,
          phone: input.phone ?? null,
          birthDate: input.birthDate ?? null,
          memberType: input.memberType,
          status: 'ACTIVE',
          libraryId: input.libraryId,
          joinedAt: new Date().toISOString(),
        };
        MOCK_MEMBERS.push(m);
        return mockDelay(m);
      }
      return client.post<Member>('/members', input);
    },
    onSuccess: (data, vars, _onMutate, mctx) => {
      void qc.invalidateQueries({ queryKey: memberKeys.lists() });
      return options?.onSuccess?.(data, vars, _onMutate, mctx);
    },
    ...options,
  });
}

export function useUpdateMemberMutation(
  options?: UseMutationOptions<Member, ApiError, { id: string; input: UpdateMemberInput }>,
) {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation<Member, ApiError, { id: string; input: UpdateMemberInput }>({
    mutationFn: ({ id, input }) => {
      if (isMockMode()) {
        const idx = MOCK_MEMBERS.findIndex((x) => x.id === id);
        if (idx < 0) return Promise.reject(new Error('not found'));
        MOCK_MEMBERS[idx] = { ...MOCK_MEMBERS[idx], ...input } as Member;
        return mockDelay(MOCK_MEMBERS[idx]);
      }
      return client.patch<Member>(`/members/${id}`, input);
    },
    onSuccess: (data, vars, _onMutate, mctx) => {
      void qc.invalidateQueries({ queryKey: memberKeys.detail(vars.id) });
      void qc.invalidateQueries({ queryKey: memberKeys.lists() });
      return options?.onSuccess?.(data, vars, _onMutate, mctx);
    },
    ...options,
  });
}

export function useDeleteMemberMutation(
  options?: UseMutationOptions<void, ApiError, string>,
) {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (id) => {
      if (isMockMode()) {
        const idx = MOCK_MEMBERS.findIndex((x) => x.id === id);
        if (idx >= 0) MOCK_MEMBERS.splice(idx, 1);
        return mockDelay(undefined);
      }
      return client.delete<void>(`/members/${id}`);
    },
    onSuccess: (data, vars, _onMutate, mctx) => {
      void qc.invalidateQueries({ queryKey: memberKeys.lists() });
      return options?.onSuccess?.(data, vars, _onMutate, mctx);
    },
    ...options,
  });
}

export function useIssueMemberCardMutation(
  options?: UseMutationOptions<MemberCard, ApiError, { memberId: string; input: IssueCardInput }>,
) {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation<MemberCard, ApiError, { memberId: string; input: IssueCardInput }>({
    mutationFn: ({ memberId, input }) => {
      if (isMockMode()) {
        const card: MemberCard = {
          id: `crd_${Date.now()}`,
          memberId,
          cardNumber: input.cardNumber ?? `9${String(Date.now()).slice(-12)}`,
          issuedAt: new Date().toISOString(),
          expiresAt: input.expiresAt ?? null,
          type: input.type ?? 'BARCODE',
        };
        MOCK_CARDS.push(card);
        return mockDelay(card);
      }
      return client.post<MemberCard>(`/members/${memberId}/cards`, input);
    },
    onSuccess: (data, vars, _onMutate, mctx) => {
      void qc.invalidateQueries({ queryKey: memberKeys.cards(vars.memberId) });
      return options?.onSuccess?.(data, vars, _onMutate, mctx);
    },
    ...options,
  });
}
