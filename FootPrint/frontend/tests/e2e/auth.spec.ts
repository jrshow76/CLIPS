/**
 * 발자국 (Foot-Print) — 인증 (AUTH) E2E 테스트
 *
 * 테스트 케이스 목록:
 * TC-AUTH-001: 회원가입 성공 → 로그인 페이지 이동
 * TC-AUTH-002: 로그인 성공 → 지도 페이지 이동
 * TC-AUTH-003: 이메일 중복 회원가입 → 오류 메시지
 * TC-AUTH-004: 잘못된 비밀번호 로그인 → 오류 메시지
 * TC-AUTH-005: 비로그인 상태로 /map 접근 → /login 리다이렉트
 * TC-AUTH-006: 로그아웃 → /login 리다이렉트
 * TC-AUTH-007: 비밀번호 확인 불일치 회원가입 → 인라인 오류
 * TC-AUTH-008: 비밀번호 강도 미달 회원가입 → 인라인 오류
 * TC-AUTH-009: 내 정보 조회 API — 필수 필드 확인
 */

import { test, expect, request as apiRequest } from '@playwright/test';
import { TEST_USER, API_BASE_URL, ROUTES } from './fixtures/test-data';
import { signupViaApi, loginViaApi } from './helpers/auth.helper';

// 테스트마다 고유한 이메일을 사용하여 계정 충돌 방지
const uniqueEmail = () => `e2e-auth-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@footprint.dev`;

test.describe('인증 (AUTH)', () => {

  // ── 정상 흐름 ─────────────────────────────────────────────────────────────

  test('TC-AUTH-001: 회원가입 성공 → 로그인 페이지 이동', async ({ page }) => {
    const email = uniqueEmail();

    await page.goto(ROUTES.signup);

    // Input 컴포넌트의 label 기반 id 생성 규칙: label 소문자 + 하이픈 (예: "이메일" → id="이메일")
    await page.locator('#이메일').fill(email);
    await page.locator('#닉네임').fill(TEST_USER.nickname);
    await page.locator('#비밀번호').fill(TEST_USER.password);
    await page.locator('#비밀번호-확인').fill(TEST_USER.password);
    await page.getByRole('button', { name: '회원가입' }).click();

    // 성공 토스트 확인
    await expect(page.getByText(/회원가입이 완료되었습니다/)).toBeVisible({ timeout: 8_000 });
    // /login 으로 이동
    await expect(page).toHaveURL(new RegExp(ROUTES.login));
  });

  test('TC-AUTH-002: 로그인 성공 → 지도 페이지 이동', async ({ page }) => {
    const email = uniqueEmail();
    // API로 먼저 계정 생성
    await signupViaApi(email, TEST_USER.password, TEST_USER.nickname);

    await page.goto(ROUTES.login);
    await page.locator('#이메일').fill(email);
    await page.locator('#비밀번호').fill(TEST_USER.password);
    await page.getByRole('button', { name: '로그인' }).click();

    // /map 으로 이동 확인
    await expect(page).toHaveURL(new RegExp(ROUTES.map), { timeout: 10_000 });
  });

  test('TC-AUTH-006: 로그아웃 → /login 리다이렉트', async ({ page }) => {
    // 이미 storageState 로 로그인된 상태에서 시작 (playwright.config.ts 설정)
    await page.goto(ROUTES.map);
    await expect(page).toHaveURL(new RegExp(ROUTES.map), { timeout: 10_000 });

    // GNB 프로필 영역 클릭 → 로그아웃 버튼
    // 닉네임 또는 프로필 아이콘으로 드롭다운 열기
    const profileDropdown = page.locator('button', { hasText: TEST_USER.nickname })
      .or(page.locator('[aria-label="프로필"]'))
      .or(page.locator('[data-testid="profile-menu"]'))
      .first();
    await profileDropdown.click();

    await page.getByRole('button', { name: '로그아웃' })
      .or(page.getByText('로그아웃'))
      .first()
      .click();

    await expect(page).toHaveURL(new RegExp(ROUTES.login), { timeout: 8_000 });
  });

  test('TC-AUTH-009: 내 정보 조회 API — 필수 필드 확인', async ({ page }) => {
    // storageState 에서 Access Token 획득
    const accessToken = await page.evaluate(() => {
      // 메모리 또는 쿠키에서 토큰을 찾는 경우 모두 처리
      return (window as { __accessToken?: string }).__accessToken
        || sessionStorage.getItem('accessToken')
        || localStorage.getItem('accessToken');
    });

    // Access Token 없으면 로그인 후 재시도
    if (!accessToken) {
      const { accessToken: token } = await loginViaApi(TEST_USER.email, TEST_USER.password);
      const ctx = await apiRequest.newContext();
      const res = await ctx.get(`${API_BASE_URL}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      await ctx.dispose();
      expect(res.ok()).toBeTruthy();
      const body = await res.json();
      expect(body.success).toBe(true);
      expect(body.data).toHaveProperty('userId');
      expect(body.data).toHaveProperty('email');
      expect(body.data).toHaveProperty('nickname');
      return;
    }

    const ctx = await apiRequest.newContext();
    const res = await ctx.get(`${API_BASE_URL}/users/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    await ctx.dispose();
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.success).toBe(true);
    expect(body.data).toHaveProperty('userId');
    expect(body.data).toHaveProperty('email');
    expect(body.data).toHaveProperty('nickname');
  });

  // ── 예외 흐름 ─────────────────────────────────────────────────────────────

  test('TC-AUTH-003: 이메일 중복 회원가입 → 오류 메시지', async ({ page }) => {
    // 기존 계정 생성
    const email = uniqueEmail();
    await signupViaApi(email, TEST_USER.password, TEST_USER.nickname);

    await page.goto(ROUTES.signup);
    await page.locator('#이메일').fill(email);
    await page.locator('#닉네임').fill(TEST_USER.nickname);
    await page.locator('#비밀번호').fill(TEST_USER.password);
    await page.locator('#비밀번호-확인').fill(TEST_USER.password);
    await page.getByRole('button', { name: '회원가입' }).click();

    // 오류 토스트 또는 인라인 오류 메시지 확인
    await expect(
      page.getByText(/이미 사용 중인 이메일|중복|EMAIL_DUPLICATED/i)
        .or(page.getByText(/회원가입에 실패했습니다/i))
    ).toBeVisible({ timeout: 8_000 });

    // 페이지 이동 없음 확인
    await expect(page).toHaveURL(new RegExp(ROUTES.signup));
  });

  test('TC-AUTH-004: 잘못된 비밀번호 로그인 → 오류 메시지', async ({ page }) => {
    const email = uniqueEmail();
    await signupViaApi(email, TEST_USER.password, TEST_USER.nickname);

    await page.goto(ROUTES.login);
    await page.locator('#이메일').fill(email);
    await page.locator('#비밀번호').fill('WrongPassword999!');
    await page.getByRole('button', { name: '로그인' }).click();

    // 오류 토스트: 계정 존재 여부 노출 없이 동일 메시지
    await expect(
      page.getByText(/이메일 또는 비밀번호가 올바르지 않습니다/i)
    ).toBeVisible({ timeout: 8_000 });

    // 로그인 페이지 유지
    await expect(page).toHaveURL(new RegExp(ROUTES.login));
  });

  test('TC-AUTH-005: 비로그인 상태로 /map 접근 → /login 리다이렉트', async ({ browser }) => {
    // 새 브라우저 컨텍스트 (storageState 없음)
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto(ROUTES.map);
    await expect(page).toHaveURL(new RegExp(ROUTES.login), { timeout: 8_000 });

    await context.close();
  });

  test('TC-AUTH-007: 비밀번호 확인 불일치 회원가입 → 인라인 오류', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto(ROUTES.signup);
    await page.locator('#이메일').fill(uniqueEmail());
    await page.locator('#닉네임').fill(TEST_USER.nickname);
    await page.locator('#비밀번호').fill(TEST_USER.password);
    await page.locator('#비밀번호-확인').fill('DifferentPass1!');
    // 포커스 이동 후 인라인 검사
    await page.locator('#비밀번호-확인').blur();

    await expect(
      page.getByText(/비밀번호가 일치하지 않습니다/i)
    ).toBeVisible({ timeout: 5_000 });

    await context.close();
  });

  test('TC-AUTH-008: 비밀번호 강도 미달 회원가입 → 인라인 오류', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto(ROUTES.signup);
    await page.locator('#이메일').fill(uniqueEmail());
    await page.locator('#닉네임').fill(TEST_USER.nickname);
    await page.locator('#비밀번호').fill('1234'); // 강도 미달
    await page.locator('#비밀번호').blur();

    await expect(
      page.getByText(/8자 이상|비밀번호/i)
    ).toBeVisible({ timeout: 5_000 });

    await context.close();
  });
});
