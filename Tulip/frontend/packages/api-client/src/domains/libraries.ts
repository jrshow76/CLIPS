/**
 * tenant-service 도서관(라이브러리) 도메인 모듈
 *
 * 가정 API:
 *   GET    /api/v1/libraries?page&size&q
 *   POST   /api/v1/libraries
 *   GET    /api/v1/libraries/{id}
 *   PATCH  /api/v1/libraries/{id}
 *   DELETE /api/v1/libraries/{id}
 *   GET    /api/v1/libraries/{id}/branches (분관)
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

export type LibraryStatus = 'ACTIVE' | 'INACTIVE' | 'CLOSED';

export type LibraryKind = 'MAIN' | 'BRANCH' | 'BOOK_MOBILE' | 'PARTNER';

export interface Library {
  id: string;
  /** 도서관 코드 (테넌트 내 unique) */
  code: string;
  name: string;
  kind: LibraryKind;
  status: LibraryStatus;
  /** 상위(본관) — 분관일 때 사용 */
  parentId?: string | null;
  address?: string;
  phone?: string;
  email?: string;
  openHours?: string;
  /** 운영 시작일 */
  openedAt?: string | null;
  /** 등록 일시 */
  createdAt: string;
  /** 분관 개수(요약용) */
  branchCount?: number;
}

export interface LibraryListQuery {
  q?: string;
  status?: LibraryStatus;
  kind?: LibraryKind;
  parentId?: string;
  page?: number;
  size?: number;
}

export interface CreateLibraryInput {
  code: string;
  name: string;
  kind: LibraryKind;
  parentId?: string | null;
  address?: string;
  phone?: string;
  email?: string;
  openHours?: string;
}

export interface UpdateLibraryInput {
  name?: string;
  kind?: LibraryKind;
  status?: LibraryStatus;
  parentId?: string | null;
  address?: string;
  phone?: string;
  email?: string;
  openHours?: string;
}

// ───────────────────────────── Query Keys ─────────────────────────────

export const libraryKeys = {
  all: ['libraries'] as const,
  lists: () => [...libraryKeys.all, 'list'] as const,
  list: (q: LibraryListQuery) => [...libraryKeys.lists(), q] as const,
  details: () => [...libraryKeys.all, 'detail'] as const,
  detail: (id: string) => [...libraryKeys.details(), id] as const,
  branches: (id: string) => [...libraryKeys.detail(id), 'branches'] as const,
};

// ───────────────────────────── Mock ─────────────────────────────

const MOCK_LIBRARIES: Library[] = [
  {
    id: 'lib_main',
    code: 'MAIN',
    name: '중앙도서관',
    kind: 'MAIN',
    status: 'ACTIVE',
    address: '서울특별시 종로구 사직로 1',
    phone: '02-1234-5678',
    openHours: '09:00~21:00',
    createdAt: '2020-01-01T00:00:00+09:00',
    branchCount: 2,
  },
  {
    id: 'lib_branch1',
    code: 'BR1',
    name: '분관A',
    kind: 'BRANCH',
    status: 'ACTIVE',
    parentId: 'lib_main',
    address: '서울특별시 강남구 테헤란로 100',
    phone: '02-3333-4444',
    createdAt: '2021-03-15T00:00:00+09:00',
  },
  {
    id: 'lib_branch2',
    code: 'BR2',
    name: '분관B',
    kind: 'BRANCH',
    status: 'INACTIVE',
    parentId: 'lib_main',
    address: '서울특별시 마포구 월드컵로 200',
    createdAt: '2022-07-01T00:00:00+09:00',
  },
];

function filterMockLibraries(q: LibraryListQuery): FlatOffsetPage<Library> {
  let items = [...MOCK_LIBRARIES];
  if (q.q) {
    const kw = q.q.toLowerCase();
    items = items.filter(
      (l) => l.name.toLowerCase().includes(kw) || l.code.toLowerCase().includes(kw),
    );
  }
  if (q.status) items = items.filter((l) => l.status === q.status);
  if (q.kind) items = items.filter((l) => l.kind === q.kind);
  if (q.parentId) items = items.filter((l) => l.parentId === q.parentId);
  const page = q.page ?? 1;
  const size = q.size ?? 20;
  const total = items.length;
  const start = (page - 1) * size;
  return { items: items.slice(start, start + size), page, size, total };
}

// ───────────────────────────── Hooks ─────────────────────────────

export function useLibrariesQuery(
  params: LibraryListQuery = {},
  options?: Omit<UseQueryOptions<FlatOffsetPage<Library>, ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<FlatOffsetPage<Library>, ApiError>({
    queryKey: libraryKeys.list(params),
    queryFn: () => {
      if (isMockMode()) return mockDelay(filterMockLibraries(params));
      return client.get<FlatOffsetPage<Library>>('/libraries', { query: compactQuery(params) });
    },
    placeholderData: (prev) => prev,
    ...options,
  });
}

export function useLibraryQuery(
  id: string | undefined,
  options?: Omit<UseQueryOptions<Library, ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<Library, ApiError>({
    queryKey: libraryKeys.detail(id ?? '__none__'),
    enabled: !!id,
    queryFn: () => {
      if (isMockMode()) {
        const l = MOCK_LIBRARIES.find((x) => x.id === id);
        if (!l) return Promise.reject(new Error('not found'));
        return mockDelay(l);
      }
      return client.get<Library>(`/libraries/${id}`);
    },
    ...options,
  });
}

export function useLibraryBranchesQuery(parentId: string | undefined) {
  return useLibrariesQuery({ parentId, size: 100 }, { enabled: !!parentId });
}

export function useCreateLibraryMutation(
  options?: UseMutationOptions<Library, ApiError, CreateLibraryInput>,
) {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation<Library, ApiError, CreateLibraryInput>({
    mutationFn: (input) => {
      if (isMockMode()) {
        const lib: Library = {
          id: `lib_${Date.now()}`,
          code: input.code,
          name: input.name,
          kind: input.kind,
          status: 'ACTIVE',
          parentId: input.parentId ?? null,
          address: input.address,
          phone: input.phone,
          email: input.email,
          openHours: input.openHours,
          createdAt: new Date().toISOString(),
        };
        MOCK_LIBRARIES.push(lib);
        return mockDelay(lib);
      }
      return client.post<Library>('/libraries', input);
    },
    onSuccess: (data, vars, _onMutate, mctx) => {
      void qc.invalidateQueries({ queryKey: libraryKeys.lists() });
      return options?.onSuccess?.(data, vars, _onMutate, mctx);
    },
    ...options,
  });
}

export function useUpdateLibraryMutation(
  options?: UseMutationOptions<Library, ApiError, { id: string; input: UpdateLibraryInput }>,
) {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation<Library, ApiError, { id: string; input: UpdateLibraryInput }>({
    mutationFn: ({ id, input }) => {
      if (isMockMode()) {
        const idx = MOCK_LIBRARIES.findIndex((x) => x.id === id);
        if (idx < 0) return Promise.reject(new Error('not found'));
        MOCK_LIBRARIES[idx] = { ...MOCK_LIBRARIES[idx], ...input } as Library;
        return mockDelay(MOCK_LIBRARIES[idx]);
      }
      return client.patch<Library>(`/libraries/${id}`, input);
    },
    onSuccess: (data, vars, _onMutate, mctx) => {
      void qc.invalidateQueries({ queryKey: libraryKeys.detail(vars.id) });
      void qc.invalidateQueries({ queryKey: libraryKeys.lists() });
      return options?.onSuccess?.(data, vars, _onMutate, mctx);
    },
    ...options,
  });
}

export function useDeleteLibraryMutation(
  options?: UseMutationOptions<void, ApiError, string>,
) {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (id) => {
      if (isMockMode()) {
        const idx = MOCK_LIBRARIES.findIndex((x) => x.id === id);
        if (idx >= 0) MOCK_LIBRARIES.splice(idx, 1);
        return mockDelay(undefined);
      }
      return client.delete<void>(`/libraries/${id}`);
    },
    onSuccess: (data, vars, _onMutate, mctx) => {
      void qc.invalidateQueries({ queryKey: libraryKeys.lists() });
      return options?.onSuccess?.(data, vars, _onMutate, mctx);
    },
    ...options,
  });
}
