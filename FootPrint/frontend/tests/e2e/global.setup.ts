/**
 * 발자국 (Foot-Print) — Playwright 전역 Setup
 *
 * 역할:
 * 1. 테스트 사용자 계정 생성 (이미 존재하면 무시)
 * 2. 로그인 후 브라우저 storageState 저장
 * 3. 저장된 storageState 를 각 project (chromium, firefox, webkit) 에서 재사용
 *
 * 실행 시점: playwright.config.ts 의 setup project 에서 가장 먼저 1회 실행
 * 저장 위치: tests/e2e/.auth/user.json
 */

import { test as setup, expect } from '@playwright/test';
import * as path from 'path';
import { TEST_USER, ROUTES, API_BASE_URL } from './fixtures/test-data';
import { signupViaApi } from './helpers/auth.helper';

const AUTH_FILE = path.join(__dirname, '.auth/user.json');

setup('전역 사용자 인증 setup', async ({ page }) => {
  // 1. 테스트 사용자 회원가입 (이미 존재하면 409 무시)
  await signupViaApi(TEST_USER.email, TEST_USER.password, TEST_USER.nickname);

  // 2. 로그인 UI 흐름
  await page.goto(ROUTES.login);

  // Input 컴포넌트: label 값이 id 로 사용됨 ("이메일" → id="이메일")
  await page.locator('#이메일').fill(TEST_USER.email);
  await page.locator('#비밀번호').fill(TEST_USER.password);
  await page.getByRole('button', { name: '로그인' }).click();

  // 로그인 성공 후 /map 이동 확인
  await expect(page).toHaveURL(new RegExp(ROUTES.map), { timeout: 15_000 });

  // 3. storageState 저장 (쿠키 + localStorage 포함)
  await page.context().storageState({ path: AUTH_FILE });
});
