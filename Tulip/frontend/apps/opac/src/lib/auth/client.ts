/**
 * opac 앱 전용 AuthClient / ApiClient 싱글톤.
 *
 * 동작은 admin과 동일하나, Keycloak client_id가 다르고(`opac-web`)
 * 비로그인 상태에서도 검색 등 일부 기능을 사용하므로 onUnauthorized 시
 * 강제 로그인 페이지로 보내지 않는다(필요한 페이지에서 개별 처리).
 */
import { createApiClient, type BaseClient } from '@tulip/api-client';
import { AuthClient, createAuthClient, createMemoryStorage } from '@tulip/auth';

function readEnv(key: string, fallback?: string): string {
  const v = process.env[key];
  if (v && v.length > 0) return v;
  if (fallback !== undefined) return fallback;
  // eslint-disable-next-line no-console
  console.warn(`[opac/auth] ${key} 환경변수가 비어 있어 fallback을 사용합니다.`);
  return '';
}

const API_BASE_URL = readEnv('NEXT_PUBLIC_API_BASE_URL', 'http://localhost:9100');
const LOCALE = readEnv('NEXT_PUBLIC_DEFAULT_LOCALE', 'ko-KR');

const authStorage = createMemoryStorage();

export const authClient: AuthClient = createAuthClient({
  config: {
    baseUrl: API_BASE_URL,
    basePath: '/api/v1/auth',
    locale: LOCALE,
  },
  storage: authStorage,
});

let currentTenantId: string | null = process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? null;

export function setActiveTenantId(tenantId: string | null): void {
  currentTenantId = tenantId;
}
export function getActiveTenantId(): string | null {
  return currentTenantId;
}

export const apiClient: BaseClient = createApiClient({
  baseUrl: API_BASE_URL,
  basePath: '/api/v1',
  locale: LOCALE,
  withCredentials: true,
  tokenProvider: {
    getAccessToken: () => authClient.getAccessToken(),
    // OPAC은 비로그인 검색을 허용하므로 401이라도 강제 redirect 하지 않는다.
    // 보호 라우트(`/me` 등)는 미들웨어가 차단.
  },
  tenantProvider: {
    getTenantId: () => currentTenantId,
  },
});

apiClient.setRefreshHandler(async () => {
  const tokens = await authClient.refresh();
  return tokens?.accessToken ?? null;
});
