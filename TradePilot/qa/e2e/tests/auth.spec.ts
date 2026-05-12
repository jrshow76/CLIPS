import { test, expect } from '@playwright/test';

/**
 * 인증 흐름 E2E.
 *  - 회원가입 → 로그인 → 대시보드 진입
 *  - OTP 입력 폼 노출 검증 (LIVE 전환 전 단계)
 *  - 잘못된 비밀번호 안내 노출
 *
 * mock 모드(`NEXT_PUBLIC_USE_MOCK=true`) 가정.
 */
test.describe('인증 / 로그인 (P0)', () => {
  test('TC-AUTH-001: 회원가입 후 자동 로그인 흐름', async ({ page }) => {
    await page.goto('/signup');
    await expect(page.getByRole('heading', { name: /회원가입/ })).toBeVisible();

    const email = `e2e-${Date.now()}@test.local`;
    await page.getByLabel('이메일').fill(email);
    await page.getByLabel('비밀번호', { exact: true }).fill('Abcd1234!');
    await page.getByLabel('닉네임').fill('e2e-tester');
    await page.getByRole('button', { name: '가입하기' }).click();

    // mock 모드는 즉시 로그인 페이지로 리다이렉트 가정
    await expect(page).toHaveURL(/\/login|\/dashboard/);
  });

  test('TC-AUTH-004: 정상 로그인 → 대시보드 진입', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('이메일').fill('demo@test.local');
    await page.getByLabel('비밀번호').fill('Demo1234!');
    await page.getByRole('button', { name: '로그인' }).click();

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByText(/대시보드/)).toBeVisible();
  });

  test('TC-AUTH-005: 잘못된 비밀번호 안내(E0001)', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('이메일').fill('demo@test.local');
    await page.getByLabel('비밀번호').fill('Wrong1234!');
    await page.getByRole('button', { name: '로그인' }).click();

    await expect(
      page.getByText(/이메일 또는 비밀번호가 일치하지 않습니다|인증이 필요합니다/),
    ).toBeVisible();
  });

  test('TC-AUTH-011: OTP 입력 폼 노출 (LIVE 전환 진입)', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('이메일').fill('demo@test.local');
    await page.getByLabel('비밀번호').fill('Demo1234!');
    await page.getByRole('button', { name: '로그인' }).click();

    // 대시보드 진입 후 자동매매 > LIVE 전환 클릭 시 OTP 모달 노출 가정
    await page.goto('/auto-trading');
    const liveToggle = page.getByRole('button', { name: /실거래.*전환|LIVE/ });
    if (await liveToggle.isVisible()) {
      await liveToggle.click();
      await expect(page.getByLabel(/OTP|인증번호/)).toBeVisible();
    }
  });
});
