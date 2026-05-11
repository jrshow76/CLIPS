/**
 * tenant-service 테넌트 도메인 모듈
 *
 * 가정 API:
 *   GET   /api/v1/tenants/me
 *   PATCH /api/v1/tenants/me
 *   GET   /api/v1/tenants/me/settings
 */
import { useQuery, type UseQueryOptions } from '@tanstack/react-query';

import { useApiClient } from '../context';
import type { ApiError } from '../errors';
import { isMockMode, mockDelay } from '../mock';

// ───────────────────────────── 타입 ─────────────────────────────

export interface Tenant {
  id: string;
  /** 테넌트 코드 (예: tnt_seoul) */
  code: string;
  /** 표시 이름 */
  name: string;
  /** 도메인 (예: seoul.tulip.example.com) */
  domain?: string;
  /** 활성 여부 */
  active: boolean;
  /** 플랜 등급 */
  plan?: 'FREE' | 'STANDARD' | 'ENTERPRISE';
  contactEmail?: string;
  createdAt: string;
}

export interface TenantSettings {
  /** 기본 로케일 */
  locale: string;
  /** 시간대 */
  timezone: string;
  /** 통화 */
  currency: string;
  /** 기능 토글 (feature flags) */
  features: Record<string, boolean>;
  /** 회원당 대출 권수 등 정책 요약 */
  policies?: Record<string, unknown>;
}

// ───────────────────────────── Query Keys ─────────────────────────────

export const tenantKeys = {
  all: ['tenants'] as const,
  me: () => [...tenantKeys.all, 'me'] as const,
  mySettings: () => [...tenantKeys.all, 'me', 'settings'] as const,
};

// ───────────────────────────── Mock ─────────────────────────────

const MOCK_TENANT: Tenant = {
  id: 'tnt_001',
  code: 'demo',
  name: '데모 도서관 그룹',
  domain: 'demo.tulip.example.com',
  active: true,
  plan: 'STANDARD',
  contactEmail: 'admin@demo.example.com',
  createdAt: '2024-01-01T00:00:00+09:00',
};

const MOCK_SETTINGS: TenantSettings = {
  locale: 'ko-KR',
  timezone: 'Asia/Seoul',
  currency: 'KRW',
  features: {
    selfCheckout: true,
    reservation: true,
    illEnabled: false,
  },
  policies: {
    maxLoans: 10,
    loanDays: 14,
  },
};

// ───────────────────────────── Hooks ─────────────────────────────

export function useMyTenantQuery(
  options?: Omit<UseQueryOptions<Tenant, ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<Tenant, ApiError>({
    queryKey: tenantKeys.me(),
    queryFn: () => {
      if (isMockMode()) return mockDelay(MOCK_TENANT);
      return client.get<Tenant>('/tenants/me');
    },
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

export function useMyTenantSettingsQuery(
  options?: Omit<UseQueryOptions<TenantSettings, ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<TenantSettings, ApiError>({
    queryKey: tenantKeys.mySettings(),
    queryFn: () => {
      if (isMockMode()) return mockDelay(MOCK_SETTINGS);
      return client.get<TenantSettings>('/tenants/me/settings');
    },
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}
