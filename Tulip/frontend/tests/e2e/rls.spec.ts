/**
 * SC-4 — RLS 격리 검증 (Phase 1-D 데모 시나리오 4)
 * ---------------------------------------------------------------
 * 시나리오 (API 레벨):
 *   Given 테넌트 A 사서 토큰과 테넌트 B 사서 토큰을 보유한다
 *   When  A 토큰으로 회원을 등록한 뒤 B 토큰으로 동일 ID 조회를 시도하면
 *   Then  404 (또는 권한없음) 응답이 반환되어야 하며
 *          ApiResponse envelope(status/error/traceId)가 표준 포맷이어야 한다.
 *
 * 주의:
 *   - 본 시나리오는 실제 백엔드(iam + member 서비스)가 가용해야 의미가 있다.
 *   - mock 모드 또는 백엔드 미가용 시 test.skip 으로 자기 보호.
 *   - DBA의 PostgreSQL RLS 회귀 자동화(`backend/tests/rls/run-rls-tests.sh`) 와
 *     본 spec(API 수준 침투)을 합쳐 누설 0건을 보장한다.
 */
import { request } from '@playwright/test';

import { E2E_MODE, expect, test } from './fixtures/auth';

const API_BASE =
  process.env.E2E_API_BASE_URL ?? 'http://localhost:8080/api/v1';
const TENANT_A = process.env.E2E_TENANT_A ?? 'demo-tenant-1';
const TENANT_B = process.env.E2E_TENANT_B ?? 'demo-tenant-2';

/** dev-only 토큰 발급 헬퍼 — iam-service 가 제공한다고 가정. */
async function obtainDevToken(tenantId: string, username: string): Promise<string | null> {
  const ctx = await request.newContext();
  try {
    const res = await ctx.post(`${API_BASE.replace(/\/api\/v1$/, '')}/api/v1/auth/login/dev`, {
      data: {
        username,
        password: process.env.E2E_PASSWORD ?? 'changeit',
        tenantId,
      },
      failOnStatusCode: false,
    });
    if (!res.ok()) return null;
    const body = (await res.json()) as { accessToken?: string; data?: { accessToken?: string } };
    return body.accessToken ?? body.data?.accessToken ?? null;
  } catch {
    return null;
  } finally {
    await ctx.dispose();
  }
}

test.describe('SC-4 RLS 격리 (API 레벨)', () => {
  test.skip(
    E2E_MODE !== 'live',
    'RLS 격리 회귀는 실 백엔드 필요 — E2E_MODE=live 에서만 수행. DB 레벨 회귀는 backend/tests/rls/run-rls-tests.sh 에서 수행.',
  );

  test('테넌트 A 토큰으로 만든 회원을 테넌트 B 토큰으로 조회 시 404', async () => {
    const tokenA = await obtainDevToken(TENANT_A, 'librarian-a@tulip.test');
    const tokenB = await obtainDevToken(TENANT_B, 'librarian-b@tulip.test');
    test.skip(!tokenA || !tokenB, 'dev 토큰 발급 불가 (iam-service 미가용)');

    const ctx = await request.newContext({
      baseURL: API_BASE,
      extraHTTPHeaders: { Authorization: `Bearer ${tokenA}` },
    });

    // 1) A 토큰으로 회원 등록
    const createRes = await ctx.post('/members', {
      data: {
        name: `RLS회원-${Date.now()}`,
        memberTypeCode: 'GENERAL',
        libraryId: 1,
        email: 'rls@example.com',
      },
    });
    expect(createRes.ok(), `A 토큰 회원 등록 실패: ${createRes.status()}`).toBeTruthy();
    const created = (await createRes.json()) as {
      status: string;
      data: { publicId: string };
      traceId?: string;
    };

    // ApiResponse 표준 envelope 검증
    expect(created.status).toBe('SUCCESS');
    expect(created.data?.publicId).toBeTruthy();
    expect(typeof (created.traceId ?? '')).toBe('string');

    const publicId = created.data.publicId;
    await ctx.dispose();

    // 2) B 토큰으로 같은 publicId 조회 → 404
    const ctxB = await request.newContext({
      baseURL: API_BASE,
      extraHTTPHeaders: { Authorization: `Bearer ${tokenB}` },
    });
    const lookupRes = await ctxB.get(`/members/${publicId}`, { failOnStatusCode: false });
    expect(lookupRes.status()).toBe(404);

    const errBody = (await lookupRes.json()) as {
      status: string;
      error?: { code: string; message: string };
      traceId?: string;
    };
    expect(errBody.status).toBe('ERROR');
    expect(errBody.error?.code).toBeTruthy();
    expect(errBody.traceId).toBeTruthy();
    await ctxB.dispose();
  });

  test('테넌트 헤더 위변조 시도(X-Tenant-Id) 가 무시되어 누설되지 않는다', async () => {
    const tokenA = await obtainDevToken(TENANT_A, 'librarian-a@tulip.test');
    test.skip(!tokenA, 'dev 토큰 발급 불가');

    const ctx = await request.newContext({
      baseURL: API_BASE,
      extraHTTPHeaders: {
        Authorization: `Bearer ${tokenA}`,
        // 의도적으로 다른 테넌트 헤더를 위조
        'X-Tenant-Id': TENANT_B,
      },
    });

    // 목록 조회 — 응답이 200이라면 모두 A 테넌트 데이터여야 한다.
    const res = await ctx.get('/members?size=5', { failOnStatusCode: false });
    if (res.ok()) {
      const body = (await res.json()) as {
        status: string;
        data: { items: Array<{ tenantId?: string }> };
      };
      expect(body.status).toBe('SUCCESS');
      // 응답 항목에 다른 테넌트가 섞이지 않아야 한다.
      for (const item of body.data.items ?? []) {
        if (item.tenantId) {
          expect(item.tenantId).toBe(TENANT_A);
        }
      }
    } else {
      // 게이트웨이가 위변조를 거부했다면 4xx (안전)
      expect(res.status()).toBeGreaterThanOrEqual(400);
      expect(res.status()).toBeLessThan(500);
    }
    await ctx.dispose();
  });
});
