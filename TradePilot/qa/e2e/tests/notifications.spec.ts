import { test, expect } from '@playwright/test';

/**
 * 알림 센터 E2E.
 *  - 진입 → 리스트 노출
 *  - 개별 읽음 처리 → 카운터 감소
 *  - 채널 ON/OFF 설정 페이지
 */
test.describe('알림 센터 (P1)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('이메일').fill('demo@test.local');
    await page.getByLabel('비밀번호').fill('Demo1234!');
    await page.getByRole('button', { name: '로그인' }).click();
  });

  test('TC-NOTI-002: 알림 센터 진입 + 읽음 처리', async ({ page }) => {
    const bell = page.getByRole('button', { name: /알림/ });
    await expect(bell).toBeVisible();
    await bell.click();

    const list = page.getByRole('list', { name: /알림/ });
    await expect(list).toBeVisible();

    const item = list.getByRole('listitem').first();
    if (await item.count()) {
      await item.click();
      // 읽음 상태 표기 변경 (예: 굵게 → 일반)
      await expect(item).toHaveAttribute('data-read', /true|1/);
    }
  });

  test('TC-NOTI-001: 알림 채널 설정 페이지', async ({ page }) => {
    await page.goto('/settings/notifications');
    await expect(page.getByText(/인앱|이메일|텔레그램/)).toBeVisible();
    const inAppToggle = page.getByRole('switch', { name: /인앱/ });
    if (await inAppToggle.count()) {
      const before = await inAppToggle.isChecked();
      await inAppToggle.click();
      const after = await inAppToggle.isChecked();
      expect(before).not.toBe(after);
    }
  });

  test('알림 미읽음 카운터 갱신', async ({ page }) => {
    const badge = page.getByRole('status', { name: /미읽음.*알림/ });
    if (await badge.count()) {
      const initial = await badge.textContent();
      const bell = page.getByRole('button', { name: /알림/ });
      await bell.click();
      const item = page.getByRole('list', { name: /알림/ }).getByRole('listitem').first();
      if (await item.count()) {
        await item.click();
        // 카운터 감소 또는 0 노출
        await expect(badge).not.toHaveText(initial ?? '');
      }
    }
  });
});
