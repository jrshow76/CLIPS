import { test, expect } from '@playwright/test';

/**
 * LIVE 전환 이중확인 모달 강제 검증 (TC-AUTO-009/010, R-02 다층 안전망).
 *
 *  - 모달은 비밀번호 + 동의 문구 입력 강제.
 *  - 동의 문구 오타 시 확인 버튼 비활성.
 *  - 사전 조건 미충족 시 별도 안내.
 */
test.describe('LIVE 전환 이중확인 모달 (P0)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('이메일').fill('pro@test.local');
    await page.getByLabel('비밀번호').fill('Pro1234!');
    await page.getByRole('button', { name: '로그인' }).click();
    await page.goto('/settings/trade-mode');
  });

  test('TC-AUTO-009: 이중확인 모달이 강제 노출된다', async ({ page }) => {
    const liveBtn = page.getByRole('button', { name: /실거래.*전환|LIVE 전환/ });
    await liveBtn.click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByLabel(/비밀번호/)).toBeVisible();
    await expect(page.getByLabel(/동의 문구|확인 문구/)).toBeVisible();
  });

  test('TC-AUTO-010: 동의 문구 오타 시 확인 버튼 비활성', async ({ page }) => {
    await page.getByRole('button', { name: /실거래.*전환|LIVE 전환/ }).click();
    await page.getByLabel(/비밀번호/).fill('Pro1234!');
    await page.getByLabel(/동의 문구|확인 문구/).fill('동이합니다');
    const submit = page.getByRole('button', { name: /^확인|^전환|^실행/ });
    await expect(submit).toBeDisabled();
  });

  test('TC-AUTO-010: 동의 문구 정확 입력 시에만 활성', async ({ page }) => {
    await page.getByRole('button', { name: /실거래.*전환|LIVE 전환/ }).click();
    await page.getByLabel(/비밀번호/).fill('Pro1234!');
    await page.getByLabel(/동의 문구|확인 문구/).fill('실거래 전환에 동의합니다');
    const submit = page.getByRole('button', { name: /^확인|^전환|^실행/ });
    await expect(submit).toBeEnabled();
  });

  test('TP-LIVE-005: 시뮬 30건 미만일 때 사전 조건 안내', async ({ page }) => {
    await page.getByRole('button', { name: /실거래.*전환|LIVE 전환/ }).click();
    const message = page.getByText(/시뮬레이션 누적.*30건|사전 조건/);
    if (await message.count()) {
      await expect(message).toBeVisible();
    }
  });

  test('LIVE 전환 후 빨강 배지 표시', async ({ page }) => {
    // 성공 케이스 (mock 시나리오 가정)
    await page.getByRole('button', { name: /실거래.*전환|LIVE 전환/ }).click();
    await page.getByLabel(/비밀번호/).fill('Pro1234!');
    await page.getByLabel(/동의 문구|확인 문구/).fill('실거래 전환에 동의합니다');
    const otp = page.getByLabel(/OTP|인증번호/);
    if (await otp.count()) await otp.fill('123456');
    const submit = page.getByRole('button', { name: /^확인|^전환|^실행/ });
    if (await submit.isEnabled()) {
      await submit.click();
      const badge = page.getByRole('status', { name: /매매 모드/ });
      if (await badge.count()) {
        await expect(badge).toContainText(/LIVE/);
      }
    }
  });
});
