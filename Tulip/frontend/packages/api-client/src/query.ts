/**
 * TanStack Query hook 팩토리
 *
 * 도메인 모듈은 아래 팩토리로 hook을 생성하여 export 한다.
 *
 * @example
 *   export const useMember = createQueryHook(
 *     (id: string) => ['members', id],
 *     (id) => client.get<Member>(`/members/${id}`)
 *   );
 */
import {
  useMutation,
  useQuery,
  type QueryKey,
  type UseMutationOptions,
  type UseMutationResult,
  type UseQueryOptions,
  type UseQueryResult,
} from '@tanstack/react-query';

import type { ApiError } from './errors';

export type AnyArgs = unknown[];

export function createQueryHook<TArgs extends AnyArgs, TData>(
  keyFn: (...args: TArgs) => QueryKey,
  queryFn: (...args: TArgs) => Promise<TData>,
) {
  return function useGeneratedQuery(
    args: TArgs,
    options?: Omit<UseQueryOptions<TData, ApiError>, 'queryKey' | 'queryFn'>,
  ): UseQueryResult<TData, ApiError> {
    return useQuery<TData, ApiError>({
      queryKey: keyFn(...args),
      queryFn: () => queryFn(...args),
      ...options,
    });
  };
}

export function createMutationHook<TVars, TData>(
  mutationFn: (vars: TVars) => Promise<TData>,
) {
  return function useGeneratedMutation(
    options?: UseMutationOptions<TData, ApiError, TVars>,
  ): UseMutationResult<TData, ApiError, TVars> {
    return useMutation<TData, ApiError, TVars>({
      mutationFn,
      ...options,
    });
  };
}

/** 도메인 모듈에서 QueryKey 생성 시 사용할 공용 prefix 유틸 */
export const queryKey = {
  /** 도메인 + 식별자 조합 */
  of: (domain: string, ...parts: Array<string | number | undefined | null | object>): QueryKey =>
    [domain, ...parts.filter((p) => p !== undefined && p !== null)] as QueryKey,
};
