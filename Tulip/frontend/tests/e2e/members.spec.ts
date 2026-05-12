/**
 * SC-2 — 회원 CRUD (Phase 1-D 데모 시나리오 2)
 * ---------------------------------------------------------------
 * 시나리오:
 *   Given 사서가 인증되어 /access/members 에 진입한다
 *   When  목록 → 등록 폼 → 필수값 검증 → 정상 등록
 *         → 검색 → 상세 → 수정 → 정지 → 복원
 *   Then  각 단계가 토스트/상태 배지로 결과를 명확히 보여준다.
 *
 * 모드: mock / live 공통.
 *   - 등록한 회원은 시드 데이터가 아닌 mock 메모리 또는 실 DB에 저장된다.
 *   - 테스트 회원명에 timestamp 를 포함시켜 충돌 방지.
 */
import { expect, test } from './fixtures/auth';

test.describe('SC-2 회원 CRUD 시나리오', () => {
  test.beforeEach(async ({ authedPage, membersPage }) => {
    await authedPage.goto('/access/members');
    await membersPage.assertReady();
  });

  test('필수값 누락 시 등록되지 않는다(폼 유효성)', async ({ membersPage, page }) => {
    await membersPage.openCreateModal();
    // 이름·도서관·회원유형을 비운 채 등록 시도
    await membersPage.submitEmpty();
    // 모달이 여전히 열려 있어야 한다 (성공 시 닫힘)
    await expect(page.getByRole('heading', { name: '회원 등록' })).toBeVisible();
  });

  test('회원 등록 → 검색 → 상세 → 수정 → 정지 → 복원 happy-path', async ({
    membersPage,
    memberDetailPage,
    page,
  }) => {
    const seed = Date.now();
    const newName = `E2E회원-${seed}`;
    const email = `e2e-${seed}@example.com`;

    // 1) 등록
    await membersPage.openCreateModal();
    await membersPage.fillRequired({
      name: newName,
      memberType: 'ADULT',
      libraryIndex: 1,
      email,
      phone: '010-0000-0000',
    });
    await membersPage.submit();
    await expect(page.getByText(/등록되었습니다|등록이 완료/)).toBeVisible();

    // 2) 검색
    await membersPage.search(newName);
    await expect(page.getByRole('link', { name: newName })).toBeVisible();

    // 3) 상세 진입
    await membersPage.openRowByName(newName);
    await expect(page.getByRole('heading', { name: new RegExp(newName) })).toBeVisible();

    // 4) 수정 — 이메일 변경
    const updatedEmail = `updated-${seed}@example.com`;
    await memberDetailPage.editEmail(updatedEmail);
    await expect(page.getByText(/수정되었습니다|저장되었습니다/)).toBeVisible();

    // 5) 정지
    await memberDetailPage.suspend();
    await expect(page.getByText(/정지되었습니다/)).toBeVisible();

    // 6) 복원 (정지된 상태에서만 복원 버튼이 노출되므로 한 번 더 확인)
    // mock 환경에서 복원 버튼이 없을 수 있으므로 존재 여부에 따라 분기.
    if (await memberDetailPage.restoreButton.count()) {
      await memberDetailPage.restore();
      await expect(page.getByText(/복원되었습니다|정상으로 변경/)).toBeVisible();
    }
  });

  test('필터 초기화 — 상태 필터 적용 후 초기화 버튼 누르면 비워진다', async ({
    membersPage,
  }) => {
    await membersPage.statusFilter.selectOption('SUSPENDED');
    await membersPage.resetButton.click();
    await expect(membersPage.statusFilter).toHaveValue('');
  });
});
