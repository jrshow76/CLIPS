import { test, expect } from '@playwright/test';

/**
 * 대시보드 진입 + 위젯 로딩 검증.
 *  - 좌측: 보유 종목 카드 / 일일 손익
 *  - 중앙: 코스피/코스닥 지수, 모드 배지
 *  - 우측: 추천주 TOP5, 최근 알림
 */
test.describe('대시보드 (P1)', () => {
  test.beforeEach(async ({ page }) => {
    // mock 자동 로그인 또는 데모 로그인
    await page.goto('/login');
    await page.getByLabel('이메일').fill('demo@test.local');
    await page.getByLabel('비밀번호').fill('Demo1234!');
    await page.getByRole('button', { name: '로그인' }).click();
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('TC-DASH-001: 보유 종목 카드 로딩', async ({ page }) => {
    const portfolioRegion = page.getByRole('region', { name: /보유 종목/ });
    await expect(portfolioRegion).toBeVisible();
  });

  test('TC-DASH-003: 일일 손익 위젯 표시', async ({ page }) => {
    await expect(page.getByText(/일일 손익|당일 손익/)).toBeVisible();
  });

  test('TC-DASH-005: 추천주 TOP5 위젯', async ({ page }) => {
    const reco = page.getByRole('region', { name: /추천주|TOP5/ });
    await expect(reco).toBeVisible();
    // 최대 5개 카드/행
    const items = reco.locator('[data-testid="reco-item"]');
    if ((await items.count()) > 0) {
      expect(await items.count()).toBeLessThanOrEqual(5);
    }
  });

  test('TC-DASH-008: SIM 모드 배지 노출 (파랑)', async ({ page }) => {
    const badge = page.getByRole('status', { name: /매매 모드/ });
    await expect(badge).toBeVisible();
    await expect(badge).toContainText(/SIM/);
  });

  test('TC-DASH-007: 진행중 시그널 카드', async ({ page }) => {
    const signals = page.getByRole('region', { name: /진행중 시그널|시그널/ });
    await expect(signals).toBeVisible();
  });
});
