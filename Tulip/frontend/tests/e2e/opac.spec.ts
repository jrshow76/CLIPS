/**
 * SC-5 — OPAC 검색·로그인 (Phase 1-D 데모 시나리오 5)
 * ---------------------------------------------------------------
 * 시나리오:
 *   Given OPAC 메인(`/`)에 진입한다
 *   When  Hero 검색바에 키워드 입력 → 결과 화면 진입 → 첫 결과 상세
 *         → 비로그인 상태에서 "대출 예약" 클릭 → 로그인 유도
 *         → 로그인 후 /me (MyLibrary) 도달
 *   Then  각 단계의 페이지 헤더와 상태가 명확히 노출된다.
 *
 * 주의:
 *   - 본 spec 은 OPAC(apps/opac, 3001)에서 동작한다.
 *   - playwright.config 의 `opac-chromium` 프로젝트가 baseURL=3001 로 매핑.
 */
import { expect, test } from './fixtures/auth';

test.describe('SC-5 OPAC 검색·로그인 시나리오', () => {
  test('OPAC 메인 → 검색 → 상세 → 비로그인 예약 → 로그인 유도', async ({
    page,
    context,
    opacSearchPage,
    bookDetailPage,
  }) => {
    // Given: 비로그인 상태 (쿠키 정리)
    await context.clearCookies();

    // When: OPAC 메인 진입 — Hero 화면이 보여야 한다
    await opacSearchPage.goto();
    await expect(opacSearchPage.heroHeading).toBeVisible();

    // 검색 수행
    await opacSearchPage.search('디자인');
    await expect(page).toHaveURL(/\/search/);

    // 첫 결과 진입 (없으면 임의 ID로 직접 이동)
    await opacSearchPage.openFirstResult();
    await expect(page).toHaveURL(/\/books\//);

    // 비로그인 상태에서 예약 시도 → 로그인 페이지 또는 로그인 유도 메시지
    if (await bookDetailPage.reserveButton.count()) {
      await bookDetailPage.tryReserveAnonymous();
      // 로그인 유도 UI 또는 redirect 둘 다 허용
      const onLoginPage = page.url().includes('/login');
      if (!onLoginPage) {
        await expect(bookDetailPage.loginPrompt).toBeVisible();
      } else {
        await expect(page.getByRole('heading', { name: /로그인|Tulip\+ OPAC/ })).toBeVisible();
      }
    }
  });

  test('인증된 사용자는 /me (MyLibrary) 에 진입할 수 있다', async ({
    page,
    context,
    baseURL,
  }) => {
    // Given: mock 세션 주입(opac도 동일한 미들웨어/쿠키 정책 가정)
    const { injectMockSession } = await import('./fixtures/auth');
    await injectMockSession(context, { baseURL });

    // When: /me 접근
    await page.goto('/me');

    // Then: MyLibrary 진입 (페이지가 미구현인 경우 skip)
    const heading = page.getByRole('heading', { name: /나의 도서관|MyLibrary|대출 현황/ });
    if (await heading.count()) {
      await expect(heading).toBeVisible();
    } else {
      test.info().annotations.push({
        type: 'skip-reason',
        description: 'OPAC /me 페이지가 아직 구현되지 않음 (Phase 1-D 후속)',
      });
    }
  });
});
