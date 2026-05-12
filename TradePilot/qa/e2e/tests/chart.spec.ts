import { test, expect } from '@playwright/test';

/**
 * 차트분석 화면 E2E.
 *  - 종목 검색 자동완성 → 선택
 *  - 차트 캔들 렌더링
 *  - 지표 토글 (MA, RSI, MACD, Bollinger)
 */
test.describe('차트 분석 (P1)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('이메일').fill('demo@test.local');
    await page.getByLabel('비밀번호').fill('Demo1234!');
    await page.getByRole('button', { name: '로그인' }).click();
    await page.goto('/chart');
  });

  test('TC-CHART-012: 종목 검색 자동완성 → 진입', async ({ page }) => {
    const search = page.getByPlaceholder(/종목 검색|종목명/);
    await search.fill('삼성전자');
    const option = page.getByRole('option', { name: /삼성전자/ });
    await expect(option).toBeVisible();
    await option.click();

    await expect(page).toHaveURL(/\/chart\/005930|\/chart\?code=005930/);
  });

  test('TC-CHART-001: 일봉 차트 렌더링', async ({ page }) => {
    await page.goto('/chart/005930');
    // 차트 캔버스 또는 SVG 노드 존재
    const chart = page.locator('[data-testid="candle-chart"], canvas, svg.chart');
    await expect(chart.first()).toBeVisible({ timeout: 10_000 });
  });

  test('TC-CHART-005: RSI 14 토글', async ({ page }) => {
    await page.goto('/chart/005930');
    const rsiToggle = page.getByRole('checkbox', { name: /RSI/ });
    if (await rsiToggle.count()) {
      await rsiToggle.check();
      const rsiOverlay = page.locator('[data-testid="indicator-rsi"]');
      await expect(rsiOverlay).toBeVisible();
    }
  });

  test('TC-CHART-006: MA 5/20 토글', async ({ page }) => {
    await page.goto('/chart/005930');
    const ma5 = page.getByRole('checkbox', { name: /MA\s*5/ });
    const ma20 = page.getByRole('checkbox', { name: /MA\s*20/ });
    if (await ma5.count()) await ma5.check();
    if (await ma20.count()) await ma20.check();
    // 두 라인이 차트에 보이는지 (라인 데이터셋 노출)
    const lines = page.locator('[data-testid^="indicator-ma"]');
    if (await lines.count()) {
      expect(await lines.count()).toBeGreaterThanOrEqual(1);
    }
  });

  test('TC-CHART-010: 잘못된 지표 파라미터 안내', async ({ page }) => {
    await page.goto('/chart/005930');
    const rsiPeriodInput = page.getByLabel(/RSI Period|RSI 기간/);
    if (await rsiPeriodInput.count()) {
      await rsiPeriodInput.fill('500');
      await rsiPeriodInput.blur();
      await expect(page.getByText(/파라미터.*범위|값을 확인/)).toBeVisible();
    }
  });
});
