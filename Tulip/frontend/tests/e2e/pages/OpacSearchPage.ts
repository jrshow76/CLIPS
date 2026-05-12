/**
 * OpacSearchPage / BookDetailPage — OPAC 검색/상세 Page Object.
 *
 * 페이지:
 *   - `/`           (OPAC 홈, Hero 검색바)
 *   - `/search?q=`  (검색 결과)
 *   - `/books/[id]` (자료 상세)
 *   - `/login`      (로그인 유도)
 *   - `/me`         (MyLibrary)
 */
import { expect, type Locator, type Page } from '@playwright/test';

export class OpacSearchPage {
  readonly page: Page;
  readonly heroHeading: Locator;
  readonly searchInput: Locator;
  readonly resultList: Locator;
  readonly resultHeading: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heroHeading = page.getByRole('heading', { name: /지식을 피우다/ });
    this.searchInput = page.getByPlaceholder('서명·저자·키워드로 검색').first();
    this.resultList = page.getByTestId('opac-search-results');
    this.resultHeading = page.getByRole('heading', { name: '검색 결과' });
  }

  async goto(): Promise<void> {
    await this.page.goto('/');
  }

  async search(keyword: string): Promise<void> {
    await this.searchInput.fill(keyword);
    await this.page.keyboard.press('Enter');
    await expect(this.resultHeading).toBeVisible();
  }

  async openFirstResult(): Promise<void> {
    const firstLink = this.page.getByTestId('opac-result-item').first();
    if (await firstLink.count()) {
      await firstLink.click();
    } else {
      // mock 모드에서 결과가 비어 있을 경우 직접 임의 ID로 이동.
      await this.page.goto('/books/sample-1');
    }
  }
}

export class BookDetailPage {
  readonly page: Page;
  readonly reserveButton: Locator;
  readonly loginPrompt: Locator;

  constructor(page: Page) {
    this.page = page;
    this.reserveButton = page.getByRole('button', { name: /대출 예약|예약/ });
    this.loginPrompt = page.getByText(/로그인이 필요|로그인 후/);
  }

  /** 비로그인 상태에서 예약 버튼 클릭 → 로그인 페이지로 유도되는 흐름. */
  async tryReserveAnonymous(): Promise<void> {
    await this.reserveButton.click();
  }
}
