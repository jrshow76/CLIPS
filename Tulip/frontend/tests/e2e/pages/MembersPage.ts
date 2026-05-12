/**
 * MembersPage / MemberDetailPage — 회원 관리 Page Object.
 *
 * 페이지: `/access/members`, `/access/members/[id]`
 *
 * 셀렉터 정책:
 *   - 가능한 한 role + accessible name 으로 잡고,
 *   - 동일 텍스트가 다수일 때만 data-testid 보강.
 */
import { expect, type Locator, type Page } from '@playwright/test';

export class MembersPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly createButton: Locator;
  readonly searchInput: Locator;
  readonly statusFilter: Locator;
  readonly resetButton: Locator;
  readonly resultTable: Locator;

  // 등록 모달
  readonly nameInput: Locator;
  readonly memberTypeSelect: Locator;
  readonly librarySelect: Locator;
  readonly emailInput: Locator;
  readonly phoneInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: '회원 관리' });
    this.createButton = page.getByRole('button', { name: '회원 등록' });
    this.searchInput = page.getByPlaceholder(/회원번호.*검색|이름.*검색/);
    this.statusFilter = page.getByLabel('상태');
    this.resetButton = page.getByRole('button', { name: '초기화' });
    this.resultTable = page.getByTestId('members-table');

    this.nameInput = page.getByLabel('이름');
    this.memberTypeSelect = page.getByLabel('회원 유형');
    this.librarySelect = page.getByLabel('소속 도서관');
    this.emailInput = page.getByLabel('이메일');
    this.phoneInput = page.getByLabel('연락처');
    this.submitButton = page.getByRole('button', { name: '등록', exact: true });
  }

  async goto(): Promise<void> {
    await this.page.goto('/access/members');
  }

  async assertReady(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  async openCreateModal(): Promise<void> {
    await this.createButton.click();
    await expect(this.page.getByRole('heading', { name: '회원 등록' })).toBeVisible();
  }

  /** 필수값 누락 시도 — 폼이 닫히지 않고 그대로여야 통과. */
  async submitEmpty(): Promise<void> {
    await this.submitButton.click();
  }

  async fillRequired(opts: {
    name: string;
    memberType?: string;
    libraryIndex?: number;
    email?: string;
    phone?: string;
  }): Promise<void> {
    await this.nameInput.fill(opts.name);
    await this.memberTypeSelect.selectOption(opts.memberType ?? 'ADULT');
    await this.librarySelect.selectOption({ index: opts.libraryIndex ?? 1 });
    if (opts.email) await this.emailInput.fill(opts.email);
    if (opts.phone) await this.phoneInput.fill(opts.phone);
  }

  async submit(): Promise<void> {
    await this.submitButton.click();
  }

  async search(keyword: string): Promise<void> {
    await this.searchInput.fill(keyword);
    await this.page.keyboard.press('Enter');
  }

  /** 검색 결과 첫 번째 행의 회원 이름 링크 클릭 → 상세 페이지로. */
  async openRowByName(name: string | RegExp): Promise<void> {
    const link = this.page.getByRole('link', { name });
    await link.first().click();
  }
}

export class MemberDetailPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly editButton: Locator;
  readonly suspendButton: Locator;
  readonly restoreButton: Locator;
  readonly emailInput: Locator;
  readonly saveButton: Locator;
  readonly statusBadge: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading');
    this.editButton = page.getByRole('button', { name: '수정' });
    this.suspendButton = page.getByRole('button', { name: '정지' });
    this.restoreButton = page.getByRole('button', { name: '복원' });
    this.emailInput = page.getByLabel('이메일');
    this.saveButton = page.getByRole('button', { name: '저장' });
    this.statusBadge = page.getByTestId('member-status');
  }

  async editEmail(newEmail: string): Promise<void> {
    await this.editButton.click();
    await this.emailInput.fill(newEmail);
    await this.saveButton.click();
  }

  async suspend(): Promise<void> {
    await this.suspendButton.click();
    // confirm 모달 안의 정지 확인 버튼.
    await this.page.getByRole('button', { name: '정지', exact: true }).last().click();
  }

  async restore(): Promise<void> {
    await this.restoreButton.click();
    await this.page.getByRole('button', { name: '복원', exact: true }).last().click();
  }
}
