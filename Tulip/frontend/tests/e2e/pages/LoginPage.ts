/**
 * LoginPage — 관리자 로그인 페이지 Page Object.
 *
 * 페이지: `/login` (admin)
 * 주요 요소:
 *  - "Keycloak으로 로그인" 버튼
 *  - 오류 메시지 (role="alert")
 */
import { expect, type Locator, type Page } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly loginButton: Locator;
  readonly errorAlert: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /Tulip\+ 관리자/ });
    this.loginButton = page.getByRole('button', { name: 'Keycloak으로 로그인' });
    this.errorAlert = page.getByRole('alert');
  }

  async goto(path: string = '/login'): Promise<void> {
    await this.page.goto(path);
  }

  async assertVisible(): Promise<void> {
    await expect(this.heading).toBeVisible();
    await expect(this.loginButton).toBeVisible();
  }

  async clickLogin(): Promise<void> {
    await this.loginButton.click();
  }
}
