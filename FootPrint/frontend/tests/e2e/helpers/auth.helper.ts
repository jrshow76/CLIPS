/**
 * 발자국 (Foot-Print) E2E 인증 헬퍼
 *
 * - loginAsTestUser: 테스트 사용자로 UI 로그인 (beforeEach 에서 재사용)
 * - setupTestUser: API 직접 호출로 사용자 생성 + Access Token 발급 (global.setup.ts 에서 사용)
 * - signupViaApi: 회원가입 API 직접 호출
 * - loginViaApi: 로그인 API 직접 호출 → Access Token 반환
 */

import { Page, APIRequestContext, request } from '@playwright/test';
import { TEST_USER, API_BASE_URL, ROUTES } from '../fixtures/test-data';

// ─── API 직접 호출 헬퍼 ──────────────────────────────────────────────────────

/**
 * 회원가입 API 직접 호출
 * 이미 가입된 경우 409 오류를 무시하고 계속 진행한다.
 */
export async function signupViaApi(
  email: string,
  password: string,
  nickname: string,
): Promise<void> {
  const ctx = await request.newContext();
  try {
    await ctx.post(`${API_BASE_URL}/auth/signup`, {
      data: { email, password, nickname },
    });
    // 409 EMAIL_DUPLICATED 는 정상 처리 (이미 존재하는 계정)
  } catch {
    // 회원가입 실패를 무시하고 이후 로그인 시도
  } finally {
    await ctx.dispose();
  }
}

/**
 * 로그인 API 직접 호출 → accessToken 반환
 * API 명세 A-02: POST /api/v1/auth/login
 * 응답: { data: { accessToken, tokenType, expiresIn, user } }
 */
export async function loginViaApi(
  email: string,
  password: string,
): Promise<{ accessToken: string }> {
  const ctx = await request.newContext();
  try {
    const res = await ctx.post(`${API_BASE_URL}/auth/login`, {
      data: { email, password },
    });
    const body = await res.json();
    return { accessToken: body.data.accessToken as string };
  } finally {
    await ctx.dispose();
  }
}

/**
 * 로그인 API 직접 호출 — APIRequestContext 버전 (global.setup.ts 에서 사용)
 */
export async function loginViaApiContext(
  apiContext: APIRequestContext,
  email: string,
  password: string,
): Promise<{ accessToken: string }> {
  const res = await apiContext.post(`${API_BASE_URL}/auth/login`, {
    data: { email, password },
  });
  const body = await res.json();
  return { accessToken: body.data.accessToken as string };
}

// ─── UI 로그인 헬퍼 ───────────────────────────────────────────────────────────

/**
 * 테스트 사용자로 UI 로그인
 * beforeEach 에서 호출하여 각 테스트 독립적으로 인증 상태를 보장한다.
 * storageState 사전 설정이 된 경우에는 호출 불필요.
 */
export async function loginAsTestUser(page: Page): Promise<void> {
  await page.goto(ROUTES.login);
  await page.locator('input[id="이메일"]').fill(TEST_USER.email);
  await page.locator('input[id="비밀번호"]').fill(TEST_USER.password);
  await page.getByRole('button', { name: '로그인' }).click();
  await page.waitForURL(`**${ROUTES.map}**`);
}

// ─── 통합 setup 헬퍼 ─────────────────────────────────────────────────────────

/**
 * 테스트 사용자 생성 + 로그인 + storageState 저장
 * global.setup.ts 에서 한 번 실행한다.
 * 저장된 storageState 는 playwright.config.ts 의 각 project 에서 재사용한다.
 */
export async function setupTestUser(page: Page): Promise<void> {
  await signupViaApi(TEST_USER.email, TEST_USER.password, TEST_USER.nickname);
  await loginAsTestUser(page);
}

/**
 * API 직접 호출로 테스트 사용자 생성 및 accessToken 획득
 * page 없이 순수 API 레벨에서 setup 시 사용한다.
 */
export async function setupTestUserViaApi(email: string, password: string, nickname: string) {
  await signupViaApi(email, password, nickname);
  return loginViaApi(email, password);
}
