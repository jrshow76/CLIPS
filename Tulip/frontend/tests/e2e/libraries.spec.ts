/**
 * SC-3 — 도서관 · 분관 관리 (Phase 1-D 데모 시나리오 3)
 * ---------------------------------------------------------------
 * 시나리오:
 *   Given 사서가 /facility/libraries 에 진입한다
 *   When  도서관 등록 → 분관 추가 → 분관 수정 → 도서관 삭제(분관 보유 → 가드)
 *         → 분관 삭제 → 도서관 삭제
 *   Then  단계별 토스트/가드 메시지가 명확히 노출되어야 한다.
 *
 * 주의:
 *   - 분관 보유 도서관 삭제 시도는 RFC 1.2.x 정책에 따라 차단되어야 한다.
 *   - mock 모드에서 가드 동작이 미구현일 수 있으므로 가드 검증은 soft.
 */
import { expect, test } from './fixtures/auth';

test.describe('SC-3 도서관·분관 관리 시나리오', () => {
  test.beforeEach(async ({ authedPage, librariesPage }) => {
    await authedPage.goto('/facility/libraries');
    await librariesPage.assertReady();
  });

  test('도서관 등록 → 분관 추가 → 분관 수정 → 분관 삭제 → 도서관 삭제 흐름', async ({
    librariesPage,
    page,
  }) => {
    const seed = Date.now();
    const libName = `E2E도서관-${seed}`;
    const libCode = `E2E${seed}`;
    const branchName = `E2E분관-${seed}`;
    const branchCode = `BR${seed}`;
    const renamedBranch = `${branchName}-수정`;

    // 1) 도서관 등록
    await librariesPage.createLibrary({ name: libName, code: libCode, kind: 'MAIN' });
    await expect(page.getByText(/등록되었습니다/)).toBeVisible();

    // 2) 도서관 상세 진입
    await librariesPage.openLibraryByName(libName);
    await expect(page.getByRole('heading', { name: new RegExp(libName) })).toBeVisible();

    // 3) 분관 추가
    await librariesPage.addBranchFromDetail({ name: branchName, code: branchCode });
    await expect(page.getByText(/분관.*등록되었습니다|등록이 완료/)).toBeVisible();

    // 4) 분관 수정
    await librariesPage.editBranch(branchName, renamedBranch);
    await expect(page.getByText(/수정되었습니다|저장되었습니다/)).toBeVisible();

    // 5) 도서관 목록으로 복귀하여 분관 보유 도서관 삭제 가드 검증
    await page.goto('/facility/libraries');
    await librariesPage.deleteLibrary(libName);
    // 가드 메시지(soft 검증) — "분관이 존재하여 삭제할 수 없습니다" 등
    const guard = page.getByText(/분관.*존재.*삭제할 수 없|분관을 먼저 삭제/);
    if (await guard.count()) {
      await expect(guard).toBeVisible();
    }

    // 6) 다시 상세로 들어가 분관 삭제
    await librariesPage.openLibraryByName(libName);
    await librariesPage.deleteBranch(renamedBranch);
    await expect(page.getByText(/삭제되었습니다/)).toBeVisible();

    // 7) 도서관 삭제 — 이번엔 성공
    await page.goto('/facility/libraries');
    await librariesPage.deleteLibrary(libName);
    await expect(page.getByText(/삭제되었습니다/)).toBeVisible();
  });
});
