/**
 * 발자국 (Foot-Print) — 장소 CRUD (PLACE) E2E 테스트
 *
 * 테스트 케이스 목록:
 * TC-PLACE-001: 장소 등록 성공 (필수 필드만)
 * TC-PLACE-002: 장소 등록 성공 (전체 필드 — 사진 제외)
 * TC-PLACE-003: 장소 수정 성공
 * TC-PLACE-004: 장소 삭제 → 목록에서 사라짐
 * TC-PLACE-005: 장소 목록 키워드 검색
 * TC-PLACE-006: 장소 목록 카테고리 필터
 * TC-PLACE-007: 장소명 빈 값 등록 시도 → 유효성 검사 오류
 * TC-PLACE-008: 미래 방문일 입력 → 유효성 검사 오류
 */

import { test, expect, request as apiRequest, Page } from '@playwright/test';
import {
  TEST_PLACE,
  TEST_PLACE_UPDATED,
  TEST_USER,
  API_BASE_URL,
  ROUTES,
  BOUNDARY,
} from './fixtures/test-data';
import { loginViaApi } from './helpers/auth.helper';

// ─── 공통 유틸 ────────────────────────────────────────────────────────────────

/**
 * 현재 로그인된 사용자의 Access Token을 가져온다.
 * storageState 또는 쿠키 기반 인증 모두 고려한다.
 */
async function getAccessToken(page: Page): Promise<string> {
  const token = await page.evaluate(() =>
    (window as { __accessToken?: string }).__accessToken
    || sessionStorage.getItem('accessToken')
    || localStorage.getItem('accessToken'),
  );
  if (!token) {
    // fallback: 테스트 사용자로 API 직접 로그인
    const { accessToken } = await loginViaApi(TEST_USER.email, TEST_USER.password);
    return accessToken;
  }
  return token;
}

/**
 * API로 장소를 직접 생성하고 placeId를 반환한다.
 * 카테고리 ID는 생성 전 API 조회로 첫 번째 기본 카테고리 ID를 가져온다.
 */
async function createPlaceViaApi(
  accessToken: string,
  overrides: Partial<typeof TEST_PLACE> = {},
): Promise<number> {
  const ctx = await apiRequest.newContext();
  try {
    // 기본 카테고리 목록에서 첫 번째 ID 조회
    const catRes = await ctx.get(`${API_BASE_URL}/categories`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const catBody = await catRes.json();
    const defaultCategoryId: number =
      catBody.data?.defaultCategories?.[0]?.categoryId
      ?? catBody.data?.[0]?.categoryId
      ?? 1;

    const res = await ctx.post(`${API_BASE_URL}/places`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: {
        name: overrides.name ?? TEST_PLACE.name,
        address: overrides.address ?? TEST_PLACE.address,
        latitude: overrides.latitude ?? TEST_PLACE.latitude,
        longitude: overrides.longitude ?? TEST_PLACE.longitude,
        visitedAt: overrides.visitedAt ?? TEST_PLACE.visitedAt,
        rating: overrides.rating ?? TEST_PLACE.rating,
        memo: overrides.memo ?? TEST_PLACE.memo,
        categoryIds: [defaultCategoryId],
        tags: overrides.tags ?? TEST_PLACE.tags,
      },
    });
    const body = await res.json();
    // API 명세 P-02 응답: data.placeId
    return (body.data?.placeId ?? body.data?.id) as number;
  } finally {
    await ctx.dispose();
  }
}

// ─── 테스트 ───────────────────────────────────────────────────────────────────

test.describe('장소 CRUD (PLACE)', () => {

  // ── 정상 흐름 ───────────────────────────────────────────────────────────────

  test('TC-PLACE-001: 장소 등록 성공 — 필수 필드만', async ({ page }) => {
    // storageState 로 이미 로그인된 상태
    await page.goto(ROUTES.placesNew);

    // 장소명 (필수)
    await page.locator('#장소명, [placeholder*="장소명"]').fill('TC-PLACE-001 테스트 장소');

    // 방문일 (필수) — 오늘 날짜
    await page.locator('input[type="date"]').first().fill('2026-05-09');

    // 위도/경도 직접 입력 필드
    await page.locator('input[id="위도"], input[placeholder*="위도"]').fill(String(TEST_PLACE.latitude));
    await page.locator('input[id="경도"], input[placeholder*="경도"]').fill(String(TEST_PLACE.longitude));

    // 카테고리 — 첫 번째 카테고리 선택
    const firstCategory = page.locator('button[class*="category"], [data-testid*="category"]').first();
    if (await firstCategory.isVisible()) {
      await firstCategory.click();
    }

    // 등록하기 버튼
    await page.getByRole('button', { name: /등록하기|저장|완료/ }).click();

    // 성공 토스트 확인
    await expect(page.getByText(/장소가 등록되었습니다/)).toBeVisible({ timeout: 10_000 });

    // 장소 상세 또는 목록 페이지로 이동
    await expect(page).toHaveURL(/\/places\/\d+|\/places/, { timeout: 10_000 });
  });

  test('TC-PLACE-002: 장소 등록 성공 — 전체 필드 (사진 제외)', async ({ page }) => {
    await page.goto(ROUTES.placesNew);

    await page.locator('#장소명, [placeholder*="장소명"]').fill(TEST_PLACE.name);
    await page.locator('input[type="date"]').first().fill(TEST_PLACE.visitedAt);
    await page.locator('input[id="위도"], input[placeholder*="위도"]').fill(String(TEST_PLACE.latitude));
    await page.locator('input[id="경도"], input[placeholder*="경도"]').fill(String(TEST_PLACE.longitude));
    await page.locator('#주소, input[placeholder*="주소"]').fill(TEST_PLACE.address);

    // 메모 입력
    const memoField = page.locator('textarea[id*="메모"], textarea[placeholder*="메모"]');
    if (await memoField.isVisible()) {
      await memoField.fill(TEST_PLACE.memo);
    }

    // 카테고리 선택
    const firstCategory = page.locator('button[class*="category"], [data-testid*="category"]').first();
    if (await firstCategory.isVisible()) {
      await firstCategory.click();
    }

    await page.getByRole('button', { name: /등록하기|저장|완료/ }).click();

    await expect(page.getByText(/장소가 등록되었습니다/)).toBeVisible({ timeout: 10_000 });
    await expect(page).toHaveURL(/\/places\/\d+|\/places/, { timeout: 10_000 });
  });

  test('TC-PLACE-003: 장소 수정 성공', async ({ page }) => {
    const accessToken = await getAccessToken(page);
    const placeId = await createPlaceViaApi(accessToken, { name: '수정 전 장소명' });

    await page.goto(`/places/${placeId}/edit`);

    // 기존 장소명이 폼에 채워진 것 확인
    await expect(page.locator('#장소명, [placeholder*="장소명"]')).not.toBeEmpty({ timeout: 8_000 });

    // 장소명 수정
    await page.locator('#장소명, [placeholder*="장소명"]').clear();
    await page.locator('#장소명, [placeholder*="장소명"]').fill(TEST_PLACE_UPDATED.name);

    await page.getByRole('button', { name: /수정하기|저장|완료/ }).click();

    // 성공 토스트 및 상세 페이지 이동
    await expect(page.getByText(/장소가 수정되었습니다/)).toBeVisible({ timeout: 10_000 });
    await expect(page).toHaveURL(new RegExp(`/places/${placeId}`), { timeout: 10_000 });

    // 상세 페이지에서 수정된 내용 확인
    await expect(page.getByText(TEST_PLACE_UPDATED.name)).toBeVisible();
  });

  test('TC-PLACE-004: 장소 삭제 → 목록에서 사라짐', async ({ page }) => {
    const accessToken = await getAccessToken(page);
    const placeId = await createPlaceViaApi(accessToken, { name: '삭제 대상 장소' });

    await page.goto(`/places/${placeId}`);

    // 삭제 버튼 클릭
    await page.getByRole('button', { name: '삭제' }).click();

    // 삭제 확인 모달
    const confirmBtn = page
      .getByRole('button', { name: '삭제' })
      .or(page.getByRole('button', { name: '확인' }))
      .last();
    await expect(confirmBtn).toBeVisible({ timeout: 5_000 });
    await confirmBtn.click();

    // 성공 토스트 및 목록 이동
    await expect(page.getByText(/장소가 삭제되었습니다/)).toBeVisible({ timeout: 10_000 });
    await expect(page).toHaveURL(new RegExp(ROUTES.places + '$'), { timeout: 8_000 });

    // 삭제된 장소 목록 미표시 확인 (API)
    const ctx = await apiRequest.newContext();
    const res = await ctx.get(`${API_BASE_URL}/places/${placeId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    await ctx.dispose();
    // 소프트 딜리트 — 본인 접근 시 404 또는 403
    expect([404, 403]).toContain(res.status());
  });

  test('TC-PLACE-005: 장소 목록 키워드 검색', async ({ page }) => {
    const accessToken = await getAccessToken(page);
    // 검색될 고유 이름으로 장소 생성
    const uniqueName = `키워드검색테스트_${Date.now()}`;
    await createPlaceViaApi(accessToken, { name: uniqueName });

    await page.goto(ROUTES.places);

    // 검색 입력창 (PlaceList 컴포넌트: type="search", placeholder="장소명, 주소로 검색...")
    const searchInput = page.locator('input[type="search"]');
    await searchInput.fill(uniqueName.slice(0, 8));
    await searchInput.press('Enter');

    // 결과 확인 (300ms debounce 후)
    await page.waitForTimeout(500);
    await expect(page.getByText(uniqueName)).toBeVisible({ timeout: 8_000 });
  });

  test('TC-PLACE-006: 장소 목록 카테고리 필터', async ({ page }) => {
    await page.goto(ROUTES.places);

    // 카테고리 필터 버튼 (PlaceList: "전체" 다음 카테고리 버튼들)
    const categoryButtons = page.locator('button').filter({ hasText: /맛집|카페|관광지/ });
    const firstCategoryBtn = categoryButtons.first();

    if (await firstCategoryBtn.isVisible()) {
      const categoryName = await firstCategoryBtn.textContent();
      await firstCategoryBtn.click();

      // URL에 category 파라미터 추가 확인
      await expect(page).toHaveURL(/category=/, { timeout: 5_000 });

      // 결과 목록에 해당 카테고리가 표시되는지 확인 (또는 빈 결과)
      await expect(
        page.getByText(categoryName!.trim()).or(page.getByText(/등록된 장소가 없습니다/))
      ).toBeVisible({ timeout: 8_000 });
    }
  });

  // ── 예외 흐름 / 유효성 검사 ───────────────────────────────────────────────

  test('TC-PLACE-007: 장소명 빈 값 등록 시도 → 유효성 검사 오류', async ({ page }) => {
    await page.goto(ROUTES.placesNew);

    // 장소명을 비워두고 다른 필드만 입력
    await page.locator('input[type="date"]').first().fill('2026-05-09');
    await page.locator('input[id="위도"], input[placeholder*="위도"]').fill(String(TEST_PLACE.latitude));
    await page.locator('input[id="경도"], input[placeholder*="경도"]').fill(String(TEST_PLACE.longitude));

    // 등록하기 버튼 클릭
    await page.getByRole('button', { name: /등록하기|저장|완료/ }).click();

    // 인라인 오류 메시지 확인
    await expect(
      page.getByText(/장소명을 입력하세요|장소명은 필수/i)
    ).toBeVisible({ timeout: 5_000 });

    // 페이지 이동 없음
    await expect(page).toHaveURL(new RegExp(ROUTES.placesNew));
  });

  test('TC-PLACE-008: 미래 방문일 입력 → 유효성 검사 오류', async ({ page }) => {
    await page.goto(ROUTES.placesNew);

    await page.locator('#장소명, [placeholder*="장소명"]').fill('미래방문일 테스트');
    await page.locator('input[id="위도"], input[placeholder*="위도"]').fill(String(TEST_PLACE.latitude));
    await page.locator('input[id="경도"], input[placeholder*="경도"]').fill(String(TEST_PLACE.longitude));

    // 미래 날짜 직접 입력 (UI 제한 우회)
    const dateInput = page.locator('input[type="date"]').first();
    await dateInput.fill(BOUNDARY.futureDateVisitedAt);
    await dateInput.blur();

    await page.getByRole('button', { name: /등록하기|저장|완료/ }).click();

    // 클라이언트 측 오류 또는 API 오류 메시지 확인
    await expect(
      page.getByText(/방문일은 오늘 이전|미래 날짜|FUTURE_DATE/i)
        .or(page.getByText(/오늘 이전 날짜/i))
    ).toBeVisible({ timeout: 8_000 });
  });
});
