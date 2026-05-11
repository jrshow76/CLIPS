/**
 * admin 앱 전용 AuthClient / ApiClient 싱글톤.
 *
 * - AuthClient: iam-service `/api/v1/auth/*` 위임 (BFF 패턴)
 * - ApiClient: Gateway 호출용 공통 클라이언트.
 *   401 시 AuthClient.refresh로 자동 재발급.
 *
 * 브라우저 단일 인스턴스로만 사용한다 (SSR/RSC 진입 시 import 금지).
 */
import { createApiClient, type BaseClient } from '@tulip/api-client';
import { AuthClient, createAuthClient, createMemoryStorage } from '@tulip/auth';

/** Public env 안전 조회 */
function readEnv(key: string, fallback?: string): string {
  const v = process.env[key];
  if (v && v.length > 0) return v;
  if (fallback !== undefined) return fallback;
  // 빌드 타임에 누락되면 즉시 알리는 편이 좋음
  // eslint-disable-next-line no-console
  console.warn(`[admin/auth] ${key} 환경변수가 비어 있어 fallback을 사용합니다.`);
  return '';
}

const API_BASE_URL = readEnv('NEXT_PUBLIC_API_BASE_URL', 'http://localhost:9100');
const LOCALE = readEnv('NEXT_PUBLIC_DEFAULT_LOCALE', 'ko-KR');
const DEFAULT_TENANT_ID = process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? undefined;

/** 인메모리 토큰 저장소 (탭 단위 단일 인스턴스) */
const authStorage = createMemoryStorage();

/** AuthClient — `/api/v1/auth/*` 호출 전담 */
export const authClient: AuthClient = createAuthClient({
  config: {
    baseUrl: API_BASE_URL,
    basePath: '/api/v1/auth',
    locale: LOCALE,
  },
  storage: authStorage,
});

/** 현재 활성 tenantId 캐시 (login 후 user.tenantId로 갱신) */
let currentTenantId: string | null = DEFAULT_TENANT_ID ?? null;

export function setActiveTenantId(tenantId: string | null): void {
  currentTenantId = tenantId;
}
export function getActiveTenantId(): string | null {
  return currentTenantId;
}

/** ApiClient — 도메인 API 호출용 */
export const apiClient: BaseClient = createApiClient({
  baseUrl: API_BASE_URL,
  basePath: '/api/v1',
  locale: LOCALE,
  withCredentials: true,
  tokenProvider: {
    getAccessToken: () => authClient.getAccessToken(),
    onUnauthorized: () => {
      // 401 + refresh 실패 시 로그인 페이지로 강제 이동
      if (typeof window !== 'undefined') {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.assign(`/login?next=${next}`);
      }
    },
  },
  tenantProvider: {
    getTenantId: () => currentTenantId,
  },
});

// 401 → AuthClient.refresh → 새 accessToken → 원 요청 재시도
apiClient.setRefreshHandler(async () => {
  const tokens = await authClient.refresh();
  return tokens?.accessToken ?? null;
});
