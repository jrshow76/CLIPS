/**
 * 전 앱 공통 상수
 */

/** 페이지네이션 표준 */
export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;
export const DEFAULT_CURSOR_LIMIT = 50;
export const MAX_CURSOR_LIMIT = 200;

/** 토큰 저장 키 (인메모리·localStorage 옵션) */
export const ACCESS_TOKEN_STORAGE_KEY = 'tulip.access_token';
export const REFRESH_TOKEN_STORAGE_KEY = 'tulip.refresh_token';
export const TENANT_STORAGE_KEY = 'tulip.tenant_id';
export const BRANCH_STORAGE_KEY = 'tulip.branch_id';
export const THEME_STORAGE_KEY = 'tulip.theme';
export const LOCALE_STORAGE_KEY = 'tulip.locale';

/** 헤더 키 */
export const HEADER_TRACE_ID = 'X-Trace-Id';
export const HEADER_TENANT_ID = 'X-Tenant-Id';
export const HEADER_BRANCH_ID = 'X-Branch-Id';
export const HEADER_IDEMPOTENCY_KEY = 'Idempotency-Key';
export const HEADER_REQUEST_ID = 'X-Request-Id';

/** TanStack Query 기본 옵션 */
export const QUERY_DEFAULT_STALE_TIME = 30 * 1000; // 30s
export const QUERY_DEFAULT_GC_TIME = 5 * 60 * 1000; // 5m
