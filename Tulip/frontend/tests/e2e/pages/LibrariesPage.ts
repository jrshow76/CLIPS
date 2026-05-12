/**
 * LibrariesPage — 도서관·분관 관리 Page Object.
 *
 * 페이지: `/facility/libraries`, `/facility/libraries/[id]`
 *
 * 주요 시나리오:
 *   - 도서관 등록 → 분관 추가 → 분관 수정 → 삭제 가드 → 분관 삭제 후 도서관 삭제
 */
import { expect, type Locator, type Page } from '@playwright/test';

export class LibrariesPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly createButton: Locator;
  readonly nameInput: Locator;
  readonly codeInput: Locator;
  readonly kindSelect: Locator;
  readonly statusSelect: Locator;
  readonly submitButton: Locator;
  readonly resultTable: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: '도서관 관리' });
    this.createButton = page.getByRole('button', { name: /도서관 등록|신규 등록/ });
    this.nameInput = page.getByLabel('도서관명');
    this.codeInput = page.getByLabel('도서관 코드');
    this.kindSelect = page.getByLabel('도서관 유형');
    this.statusSelect = page.getByLabel('상태');
    this.submitButton = page.getByRole('button', { name: '등록', exact: true });
    this.resultTable = page.getByTestId('libraries-table');
  }

  async goto(): Promise<void> {
    await this.page.goto('/facility/libraries');
  }

  async assertReady(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  async createLibrary(opts: {
    name: string;
    code: string;
    kind?: 'MAIN' | 'BRANCH' | 'BOOK_MOBILE' | 'PARTNER';
  }): Promise<void> {
    await this.createButton.click();
    await expect(this.page.getByRole('heading', { name: /도서관 등록|신규 등록/ })).toBeVisible();
    await this.nameInput.fill(opts.name);
    await this.codeInput.fill(opts.code);
    await this.kindSelect.selectOption(opts.kind ?? 'MAIN');
    await this.submitButton.click();
  }

  async openLibraryByName(name: string): Promise<void> {
    await this.page.getByRole('link', { name }).first().click();
  }

  /** 도서관 상세 화면에서 분관 추가. */
  async addBranchFromDetail(opts: { name: string; code: string }): Promise<void> {
    await this.page.getByRole('button', { name: /분관 추가|분관 등록/ }).click();
    await this.page.getByLabel('분관명').fill(opts.name);
    await this.page.getByLabel('분관 코드').fill(opts.code);
    await this.page.getByRole('button', { name: '등록', exact: true }).click();
  }

  async editBranch(branchName: string, newName: string): Promise<void> {
    const row = this.page.getByRole('row', { name: new RegExp(branchName) });
    await row.getByRole('button', { name: '수정' }).click();
    await this.page.getByLabel('분관명').fill(newName);
    await this.page.getByRole('button', { name: '저장' }).click();
  }

  async deleteBranch(branchName: string): Promise<void> {
    const row = this.page.getByRole('row', { name: new RegExp(branchName) });
    await row.getByRole('button', { name: '삭제' }).click();
    await this.page.getByRole('button', { name: '삭제', exact: true }).last().click();
  }

  /** 도서관 삭제 시도. 분관이 있다면 가드 메시지가 노출되어야 한다. */
  async deleteLibrary(libraryName: string): Promise<void> {
    const row = this.page.getByRole('row', { name: new RegExp(libraryName) });
    await row.getByRole('button', { name: '삭제' }).click();
    await this.page.getByRole('button', { name: '삭제', exact: true }).last().click();
  }
}
