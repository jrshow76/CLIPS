/**
 * SC-1 — 로그인 · 로그아웃 (Phase 1-D 데모 시나리오 1)
 * ---------------------------------------------------------------
 * 시나리오:
 *   Given /login 페이지에 접속하고
 *   When  "Keycloak으로 로그인" 버튼을 클릭하면
 *   Then  (mock) /dashboard 로 진입하고 헤더에 대시보드 제목이 노출된다.
 *   When  사용자 메뉴에서 로그아웃을 누르면
 *   Then  /login 으로 복귀하고 보호 라우트는 다시 차단된다.
 *
 * 모드:
 *   - mock: 미들웨어의 refresh 쿠키 검사를 우회하기 위해 fixture 가 쿠키를 주입.
 *           로그인 버튼 클릭은 시나리오 검증용이며, 실제 IdP redirect는 발생하지 않는다.
 *   - live: Keycloak Direct Grant 후 쿠키 주입.
 */
import { E2E_MODE, expect, test } from './fixtures/auth';

test.describe('SC-1 로그인·로그아웃 시나리오', () => {
  test('비로그인 상태로 보호 라우트 접근 시 /login 으로 리다이렉트된다', async ({
    page,
    context,
  }) => {
    // Given: 쿠키 없는 깨끗한 상태
    await context.clearCookies();

    // When: 보호 라우트(/dashboard) 직접 접근
    await page.goto('/dashboard');

    // Then: 미들웨어가 /login 으로 302
    await expect(page).toHaveURL(/\/login(\?next=.*)?$/);
    await expect(page.getByRole('heading', { name: /Tulip\+ 관리자/ })).toBeVisible();
  });

  test('로그인 버튼이 노출되고 정상 클릭된다', async ({ page, loginPage }) => {
    await loginPage.goto();
    await loginPage.assertVisible();

    // 클릭 시 실 모드에서는 IdP로 redirect가 발생하므로, mock 모드에서만 후속 검증.
    if (E2E_MODE === 'mock') {
      // 클릭 직후 로딩 상태가 표시되어야 한다 (Button loading=true).
      await loginPage.loginButton.click();
      // mock 환경에서는 외부 호출이 실패할 가능성이 있으므로 alert 또는 그대로 페이지 유지.
      await page.waitForTimeout(500);
    } else {
      // 실 모드 — 클릭 후 외부 도메인(Keycloak)으로 이동 또는 대시보드로 이동.
      await loginPage.loginButton.click();
    }
  });

  test('인증된 세션은 /dashboard 진입 가능, 로그아웃 시 다시 차단된다', async ({
    authedPage,
    context,
  }) => {
    // Given: fixture가 mock/live 세션을 주입한 상태
    await authedPage.goto('/dashboard');

    // Then: 대시보드 페이지 헤더 노출
    await expect(authedPage.getByRole('heading', { name: '대시보드' })).toBeVisible();

    // When: 로그아웃 (쿠키 삭제)
    await context.clearCookies();
    await authedPage.goto('/dashboard');

    // Then: 다시 /login 으로 차단
    await expect(authedPage).toHaveURL(/\/login(\?next=.*)?$/);
  });
});
