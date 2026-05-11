/**
 * Playwright E2E — 회원 관리 시나리오 (Phase 1-D QA 실행 예정)
 *
 * 본 파일은 시나리오 정의만 제공한다.
 * 실행 환경(Playwright 설치/설정·테스트 사용자 계정·테스트 테넌트 등)은
 * Phase 1-D QA가 별도 PR에서 구성한다.
 *
 * 전제:
 *   - admin 앱이 http://localhost:3000 에서 구동 중
 *   - NEXT_PUBLIC_USE_MOCK=true (또는 시드된 회원 데이터)
 *   - 테스트 사용자: scope에 member:read, member:write 포함
 */
import { expect, test } from '@playwright/test';

const BASE = process.env.E2E_BASE_URL ?? 'http://localhost:3000';
const USER = process.env.E2E_USER_NAME ?? 'tester';

test.describe('회원 관리 — 등록·검색·상세·수정·정지', () => {
  test.beforeEach(async ({ page }) => {
    // 이미 인증된 세션을 사용하는 storageState 가정.
    // (Phase 1-D QA가 globalSetup으로 토큰 주입)
    await page.goto(`${BASE}/access/members`);
    await expect(page.getByRole('heading', { name: '회원 관리' })).toBeVisible();
  });

  test('회원 등록 → 검색 → 상세 → 수정 → 정지 시나리오', async ({ page }) => {
    const newName = `테스트회원-${Date.now()}`;

    // 1. 회원 등록 모달 열기
    await page.getByRole('button', { name: '회원 등록' }).click();
    await expect(page.getByRole('heading', { name: '회원 등록' })).toBeVisible();

    // 2. 필수 항목 입력
    await page.getByLabel('이름').fill(newName);
    await page.getByLabel('회원 유형').selectOption('ADULT');
    await page.getByLabel('소속 도서관').selectOption({ index: 1 });
    await page.getByLabel('이메일').fill('e2e@example.com');
    await page.getByLabel('연락처').fill('010-0000-0000');

    // 3. 저장
    await page.getByRole('button', { name: '등록' }).click();
    await expect(page.getByText('회원이 등록되었습니다.')).toBeVisible();

    // 4. 검색
    await page.getByPlaceholder('회원번호 · 이름 · 연락처 검색').fill(newName);
    await page.keyboard.press('Enter');
    await expect(page.getByRole('link', { name: newName })).toBeVisible();

    // 5. 상세 진입
    await page.getByRole('link', { name: newName }).click();
    await expect(page.getByRole('heading', { name: new RegExp(newName) })).toBeVisible();

    // 6. 수정 모달
    await page.getByRole('button', { name: '수정' }).click();
    await page.getByLabel('이메일').fill(`updated-${USER}@example.com`);
    await page.getByRole('button', { name: '저장' }).click();
    await expect(page.getByText('회원 정보가 수정되었습니다.')).toBeVisible();

    // 7. 정지
    await page.getByRole('button', { name: '정지' }).click();
    await page.getByRole('button', { name: '정지', exact: true }).last().click();
    await expect(page.getByText('회원이 정지되었습니다.')).toBeVisible();
    await expect(page.getByText('정지')).toBeVisible();
  });

  test('필터 초기화 동작', async ({ page }) => {
    await page.getByLabel('상태').selectOption('SUSPENDED');
    await page.getByRole('button', { name: '초기화' }).click();
    await expect(page.getByLabel('상태')).toHaveValue('');
  });
});
