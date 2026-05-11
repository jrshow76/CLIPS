/**
 * @tulip/api-client
 *
 * - 공통 응답 envelope 타입 (`ApiResponse<T>`)
 * - ofetch 기반 BaseClient (인터셉터로 인증/테넌트/traceId 자동 첨부)
 * - TanStack Query hook 팩토리 (createQueryHook, createMutationHook)
 * - 도메인별 API 모듈은 Phase 1-B 이후 추가
 */
export * from './types';
export * from './errors';
export * from './client';
export * from './query';
export * from './trace';
