import { test, expect } from '@playwright/test';

/**
 * 자동매매 흐름 E2E.
 *  - 전략 신규 등록 → 활성화
 *  - SIM 모드에서 LIVE 전환 시도 차단 (사전 조건 미달)
 *  - Kill Switch 버튼 노출 / 클릭 시 확인 모달
 */
test.describe('자동매매 (P0)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('이메일').fill('demo@test.local');
    await page.getByLabel('비밀번호').fill('Demo1234!');
    await page.getByRole('button', { name: '로그인' }).click();
    await page.goto('/auto-trading');
  });

  test('TC-AUTO-001: 전략 신규 등록 폼 표시 + 저장', async ({ page }) => {
    await page.getByRole('button', { name: /전략 등록|신규 전략/ }).click();
    await page.getByLabel('전략명').fill('E2E 골든크로스');
    await page.getByLabel(/진입 조건|진입조건/).fill('MA5 > MA20');
    await page.getByLabel(/청산 조건|청산조건/).fill('MA5 < MA20');
    await page.getByRole('button', { name: '저장' }).click();
    await expect(page.getByText(/등록 완료|저장되었습니다/)).toBeVisible();
  });

  test('TC-AUTO-005: 전략 활성/비활성 토글', async ({ page }) => {
    const row = page.locator('[data-testid="strategy-row"]').first();
    if (await row.count()) {
      const toggle = row.getByRole('switch');
      const before = await toggle.isChecked();
      await toggle.click();
      const after = await toggle.isChecked();
      expect(before).not.toBe(after);
    }
  });

  test('TC-AUTO-009/SIM→LIVE 전환 시도: 사전조건 미달 차단', async ({ page }) => {
    const liveToggle = page.getByRole('button', { name: /실거래.*전환|LIVE 전환/ });
    if (await liveToggle.count()) {
      await liveToggle.click();
      // 이중확인 모달 또는 사전 조건 안내
      await expect(
        page.getByText(
          /실거래 전환 사전 조건|시뮬레이션 누적|약관 동의|본인인증/,
        ),
      ).toBeVisible();
    }
  });

  test('TP-KILL-001: Kill Switch 버튼 상시 노출 + 확인 모달', async ({ page }) => {
    const killBtn = page.getByRole('button', { name: /Kill Switch|비상 정지|비상정지/ });
    await expect(killBtn).toBeVisible();
    await killBtn.click();
    await expect(page.getByText(/비상정지를 실행|모든 주문이 취소/)).toBeVisible();
    const confirm = page.getByRole('button', { name: /확인|실행/ });
    if (await confirm.count()) {
      await confirm.click();
      // 5초 SLA 내 자동매매 OFF 상태 안내
      await expect(page.getByText(/자동매매가 중단|비상정지 완료/)).toBeVisible({
        timeout: 7_000,
      });
    }
  });
});
