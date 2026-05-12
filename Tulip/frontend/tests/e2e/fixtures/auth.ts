/**
 * 인증 픽스처 — Tulip+ E2E
 * ---------------------------------------------------------------
 *  - mock 모드 (기본): 환경 변수 NEXT_PUBLIC_USE_MOCK=true 가정.
 *      Keycloak/iam-service 없이 진입할 수 있도록
 *      미들웨어가 검사하는 refresh 쿠키(tulip_refresh)만 주입한다.
 *
 *  - 실 모드 (E2E_MODE=live): Keycloak Direct Grant로 토큰을 받아
 *      Set-Cookie 응답을 신뢰하고 storageState 형태로 주입한다.
 *
 * Page Object 패턴과 결합하여 모든 spec에서 `test`를 본 모듈에서 import한다.
 */
import { test as base, type BrowserContext, type Page } from '@playwright/test';

import { DashboardPage } from '../pages/DashboardPage';
import { LibrariesPage } from '../pages/LibrariesPage';
import { LoginPage } from '../pages/LoginPage';
import { MemberDetailPage, MembersPage } from '../pages/MembersPage';
import { BookDetailPage, OpacSearchPage } from '../pages/OpacSearchPage';

const MODE = (process.env.E2E_MODE ?? 'mock') as 'mock' | 'live';
const COOKIE_NAME = process.env.NEXT_PUBLIC_AUTH_COOKIE_NAME ?? 'tulip_refresh';

/** mock 환경에서 사용할 가짜 refresh token 값 — 형식만 맞으면 미들웨어 통과. */
const MOCK_REFRESH = 'e2e.mock.refresh.token';

/**
 * mock 모드 — refresh 쿠키만 주입하면 미들웨어가 통과시키고,
 * 페이지 마운트 시 useAuth.bootstrap이 MSW(또는 mock API)에서 /me 응답을 받는다.
 */
export async function injectMockSession(
  context: BrowserContext,
  opts: { tenantId?: string; baseURL?: string } = {},
): Promise<void> {
  const url = opts.baseURL ?? 'http://localhost:3000';
  const { hostname } = new URL(url);
  await context.addCookies([
    {
      name: COOKIE_NAME,
      value: MOCK_REFRESH,
      domain: hostname,
      path: '/',
      httpOnly: false, // 미들웨어가 cookies.has() 만 검사하므로 httpOnly 불요
      secure: false,
      sameSite: 'Lax',
    },
    {
      // mock API가 테넌트 분리 시 참조할 수 있도록 비 httpOnly cookie도 함께.
      name: 'tulip_e2e_tenant',
      value: opts.tenantId ?? 'demo-tenant-1',
      domain: hostname,
      path: '/',
      httpOnly: false,
      secure: false,
      sameSite: 'Lax',
    },
  ]);
}

/**
 * 실 모드 — Keycloak Direct Grant (Resource Owner Password) 로 토큰을 받고
 * iam-service `/auth/login/session` (있다고 가정) 이나 직접 쿠키 주입으로 세션 구성.
 *
 * 실제 백엔드 인증 흐름이 BFF + httpOnly 쿠키이므로, 이 함수는
 * iam-service의 dev-only 엔드포인트를 호출해 쿠키를 받는 형태로 구현.
 * 백엔드 미가용 시 호출 자체에 실패 → 테스트는 skip 마커로 보호된다.
 */
export async function loginViaKeycloak(
  context: BrowserContext,
  opts: { username: string; password: string; tenantId?: string },
): Promise<void> {
  const iamBase = process.env.E2E_IAM_BASE_URL ?? 'http://localhost:8080';
  const res = await context.request.post(`${iamBase}/api/v1/auth/login/dev`, {
    data: {
      username: opts.username,
      password: opts.password,
      tenantId: opts.tenantId ?? 'demo-tenant-1',
    },
    failOnStatusCode: false,
  });
  if (!res.ok()) {
    throw new Error(
      `실 모드 로그인 실패 (HTTP ${res.status()}). iam-service /auth/login/dev 활성화 필요.`,
    );
  }
}

/** 모드에 따라 자동 분기 — spec에서는 await authenticate(...) 한 줄로 끝. */
export async function authenticate(
  context: BrowserContext,
  opts: { tenantId?: string; username?: string; baseURL?: string } = {},
): Promise<void> {
  if (MODE === 'live') {
    await loginViaKeycloak(context, {
      username: opts.username ?? 'librarian@demo-tenant-1',
      password: process.env.E2E_PASSWORD ?? 'changeit',
      tenantId: opts.tenantId,
    });
    return;
  }
  await injectMockSession(context, opts);
}

/** Playwright fixture 확장 — Page Object 자동 주입. */
type TulipFixtures = {
  authedPage: Page;
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
  membersPage: MembersPage;
  memberDetailPage: MemberDetailPage;
  librariesPage: LibrariesPage;
  opacSearchPage: OpacSearchPage;
  bookDetailPage: BookDetailPage;
};

export const test = base.extend<TulipFixtures>({
  /** 미리 인증된 페이지(기본 admin). */
  authedPage: async ({ context, page, baseURL }, use) => {
    await authenticate(context, { baseURL });
    await use(page);
  },
  loginPage: async ({ page }, use) => use(new LoginPage(page)),
  dashboardPage: async ({ page }, use) => use(new DashboardPage(page)),
  membersPage: async ({ page }, use) => use(new MembersPage(page)),
  memberDetailPage: async ({ page }, use) => use(new MemberDetailPage(page)),
  librariesPage: async ({ page }, use) => use(new LibrariesPage(page)),
  opacSearchPage: async ({ page }, use) => use(new OpacSearchPage(page)),
  bookDetailPage: async ({ page }, use) => use(new BookDetailPage(page)),
});

export { expect } from '@playwright/test';
export const E2E_MODE = MODE;
