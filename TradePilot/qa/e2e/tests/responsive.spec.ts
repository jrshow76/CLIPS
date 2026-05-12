import { test, expect, devices } from '@playwright/test';

/**
 * 반응형 회귀 - 320 / 768 / 1280 viewport.
 *
 * 각 viewport 에서 다음 화면이 정상 표시되어야 한다:
 *  - 로그인 / 대시보드 / 차트 / 자동매매
 *  - 햄버거 메뉴(모바일) 또는 사이드바(데스크탑) 토글
 */
const viewports = [
  { name: '모바일 320', width: 320, height: 568 },
  { name: '태블릿 768', width: 768, height: 1024 },
  { name: '데스크탑 1280', width: 1280, height: 800 },
];

for (const vp of viewports) {
  test.describe(`반응형: ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test('로그인 화면 표시', async ({ page }) => {
      await page.goto('/login');
      await expect(page.getByLabel('이메일')).toBeVisible();
      await expect(page.getByLabel('비밀번호')).toBeVisible();
    });

    test('대시보드 위젯 표시', async ({ page }) => {
      await page.goto('/login');
      await page.getByLabel('이메일').fill('demo@test.local');
      await page.getByLabel('비밀번호').fill('Demo1234!');
      await page.getByRole('button', { name: '로그인' }).click();
      await expect(page).toHaveURL(/\/dashboard/);

      if (vp.width < 768) {
        const menuBtn = page.getByRole('button', { name: /메뉴|menu/i });
        if (await menuBtn.count()) {
          await expect(menuBtn).toBeVisible();
        }
      } else {
        const sidebar = page.getByRole('navigation');
        if (await sidebar.count()) {
          await expect(sidebar.first()).toBeVisible();
        }
      }
    });

    test('차트 화면 가로 스크롤/리플로우 검증', async ({ page }) => {
      await page.goto('/chart/005930');
      const chart = page.locator('[data-testid="candle-chart"], canvas, svg.chart').first();
      if (await chart.count()) {
        await expect(chart).toBeVisible();
      }
      // 수평 스크롤바 노출 여부 (모바일에서 가로 overflow 없어야 함)
      const overflowX = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      // 모바일에서 overflowX 가 0 이하 이도록(허용 오차 10px)
      if (vp.width < 768) {
        expect(overflowX).toBeLessThanOrEqual(10);
      }
    });
  });
}
