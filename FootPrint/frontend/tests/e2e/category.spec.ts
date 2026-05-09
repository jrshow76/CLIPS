/**
 * 발자국 (Foot-Print) — 카테고리 관리 (CATEGORY) E2E 테스트
 *
 * 테스트 케이스 목록:
 * TC-CAT-001: 사용자 카테고리 생성 성공
 * TC-CAT-002: 카테고리 수정 성공
 * TC-CAT-003: 카테고리 삭제 성공
 * TC-CAT-004: 기본 카테고리는 수정/삭제 버튼 비활성화 (UI) + API 403
 *
 * API 명세 참조: api_requirements.md 6.4 카테고리 (Category)
 * - GET    /api/v1/categories               → 목록 조회 (defaultCategories, userCategories 분리)
 * - POST   /api/v1/categories               → 생성 (201)
 * - PUT    /api/v1/categories/{categoryId}  → 수정 (200), 기본 카테고리 403
 * - DELETE /api/v1/categories/{categoryId}  → 삭제 (200), 기본 카테고리 403
 */

import { test, expect, request as apiRequest, Page } from '@playwright/test';
import { TEST_CATEGORY, TEST_CATEGORY_UPDATED, TEST_USER, API_BASE_URL, ROUTES } from './fixtures/test-data';
import { loginViaApi } from './helpers/auth.helper';

// ─── 공통 유틸 ────────────────────────────────────────────────────────────────

async function getAccessToken(page: Page): Promise<string> {
  const token = await page.evaluate(() =>
    (window as { __accessToken?: string }).__accessToken
    || sessionStorage.getItem('accessToken')
    || localStorage.getItem('accessToken'),
  );
  if (!token) {
    const { accessToken } = await loginViaApi(TEST_USER.email, TEST_USER.password);
    return accessToken;
  }
  return token;
}

/** API로 사용자 정의 카테고리를 생성하고 categoryId를 반환한다 */
async function createCategoryViaApi(
  accessToken: string,
  name: string,
): Promise<number> {
  const ctx = await apiRequest.newContext();
  try {
    const res = await ctx.post(`${API_BASE_URL}/categories`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { name, color: TEST_CATEGORY.color, icon: TEST_CATEGORY.icon },
    });
    const body = await res.json();
    // API 명세: data.categoryId
    return (body.data?.categoryId ?? body.data?.id) as number;
  } finally {
    await ctx.dispose();
  }
}

/** API로 기본 카테고리 목록을 조회하고 첫 번째 기본 카테고리 ID를 반환한다 */
async function getDefaultCategoryId(accessToken: string): Promise<number> {
  const ctx = await apiRequest.newContext();
  try {
    const res = await ctx.get(`${API_BASE_URL}/categories`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const body = await res.json();
    const defaultCats = body.data?.defaultCategories ?? body.data?.filter?.((c: { isDefault: boolean }) => c.isDefault) ?? [];
    return (defaultCats[0]?.categoryId ?? defaultCats[0]?.id) as number;
  } finally {
    await ctx.dispose();
  }
}

// ─── 테스트 ───────────────────────────────────────────────────────────────────

test.describe('카테고리 (CATEGORY)', () => {

  // ── 정상 흐름 ───────────────────────────────────────────────────────────────

  test('TC-CAT-001: 사용자 카테고리 생성 성공', async ({ page }) => {
    const accessToken = await getAccessToken(page);
    const ctx = await apiRequest.newContext();

    const uniqueName = `E2E카테고리_${Date.now()}`;
    const res = await ctx.post(`${API_BASE_URL}/categories`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { name: uniqueName, color: TEST_CATEGORY.color, icon: TEST_CATEGORY.icon },
    });
    await ctx.dispose();

    // API 명세: 201 Created
    expect(res.status()).toBe(201);
    const body = await res.json();
    expect(body.success).toBe(true);
    // API 명세: data.isDefault: false, data.placeCount: 0
    expect(body.data.name).toBe(uniqueName);
    expect(body.data.color).toBe(TEST_CATEGORY.color);
    expect(body.data.isDefault).toBe(false);
    expect(body.data.placeCount).toBe(0);
  });

  test('TC-CAT-002: 카테고리 수정 성공', async ({ page }) => {
    const accessToken = await getAccessToken(page);
    const categoryId = await createCategoryViaApi(accessToken, `수정전카테고리_${Date.now()}`);

    const ctx = await apiRequest.newContext();
    const res = await ctx.put(`${API_BASE_URL}/categories/${categoryId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { name: TEST_CATEGORY_UPDATED.name, color: TEST_CATEGORY_UPDATED.color },
    });
    await ctx.dispose();

    // API 명세: 200 OK
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.success).toBe(true);
    expect(body.data.color).toBe(TEST_CATEGORY_UPDATED.color);
    expect(body.data.name).toBe(TEST_CATEGORY_UPDATED.name);
  });

  test('TC-CAT-003: 카테고리 삭제 성공 (사용되지 않는 카테고리)', async ({ page }) => {
    const accessToken = await getAccessToken(page);
    const categoryId = await createCategoryViaApi(accessToken, `삭제대상_${Date.now()}`);

    const ctx = await apiRequest.newContext();
    const res = await ctx.delete(`${API_BASE_URL}/categories/${categoryId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    await ctx.dispose();

    // API 명세: 200 OK
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.success).toBe(true);

    // 삭제 후 목록 재조회 — 해당 ID 미포함 확인
    const ctx2 = await apiRequest.newContext();
    const listRes = await ctx2.get(`${API_BASE_URL}/categories`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    await ctx2.dispose();
    const listBody = await listRes.json();
    const userCats = listBody.data?.userCategories ?? [];
    const exists = userCats.some(
      (c: { categoryId: number; id: number }) =>
        c.categoryId === categoryId || c.id === categoryId,
    );
    expect(exists).toBe(false);
  });

  test('TC-CAT-004: 기본 카테고리 수정/삭제 — UI 버튼 비활성화 및 API 403', async ({ page }) => {
    const accessToken = await getAccessToken(page);
    const defaultCategoryId = await getDefaultCategoryId(accessToken);

    // ── UI 검증: 기본 카테고리 수정/삭제 버튼 미표시 또는 비활성화 ──
    await page.goto(ROUTES.categories);

    // 기본 카테고리 섹션에서 수정 버튼이 없거나 비활성화 확인
    const defaultSection = page.locator('text=기본 카테고리').locator('..');
    if (await defaultSection.isVisible()) {
      const editBtn = defaultSection.getByRole('button', { name: /수정/ }).first();
      if (await editBtn.isVisible()) {
        // 버튼이 있다면 disabled 상태여야 함
        await expect(editBtn).toBeDisabled();
      }
      // 버튼이 아예 없어도 통과 (화면 정의서: [편집 불가] 레이블)
    }

    // ── API 검증: 기본 카테고리 수정 시도 → 403 FORBIDDEN ──
    const ctx = await apiRequest.newContext();
    const editRes = await ctx.put(`${API_BASE_URL}/categories/${defaultCategoryId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { name: '수정시도', color: '#000000' },
    });
    // API 명세: 403 FORBIDDEN, "기본 카테고리는 수정하거나 삭제할 수 없습니다."
    expect(editRes.status()).toBe(403);
    const editBody = await editRes.json();
    expect(editBody.success).toBe(false);

    // ── API 검증: 기본 카테고리 삭제 시도 → 403 FORBIDDEN ──
    const deleteRes = await ctx.delete(`${API_BASE_URL}/categories/${defaultCategoryId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    expect(deleteRes.status()).toBe(403);
    const deleteBody = await deleteRes.json();
    expect(deleteBody.success).toBe(false);

    await ctx.dispose();
  });
});
