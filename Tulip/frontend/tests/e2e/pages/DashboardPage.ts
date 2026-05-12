/**
 * DashboardPage — 관리자 대시보드 Page Object.
 *
 * 페이지: `/dashboard` (admin, (shell) 그룹)
 *
 * 주요 요소:
 *  - 페이지 헤더("대시보드")
 *  - KPI 카드 4개 (회원수/대출수/연체수/오늘 입고)
 *  - 사이드바 (회원관리 / 도서관관리 등)
 *  - 헤더의 사용자 메뉴 (로그아웃 진입)
 */
import { expect, type Locator, type Page } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly kpiGrid: Locator;
  readonly sidebar: Locator;
  readonly userMenuTrigger: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: '대시보드' });
    this.kpiGrid = page.getByTestId('dashboard-kpi-grid');
    this.sidebar = page.getByRole('navigation', { name: /사이드바|Sidebar/ });
    this.userMenuTrigger = page.getByTestId('app-user-menu');
  }

  async goto(): Promise<void> {
    await this.page.goto('/dashboard');
  }

  async assertReady(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  /** 좌측 사이드바에서 메뉴 항목 클릭. */
  async openSidebarItem(label: RegExp | string): Promise<void> {
    const link = this.page.getByRole('link', { name: label });
    await link.first().click();
  }

  /** 사용자 메뉴를 통해 로그아웃 수행 — mock 모드는 쿠키만 삭제. */
  async logout(): Promise<void> {
    // 사용자 메뉴 트리거가 testid로 있으면 그것을 우선, 없으면 텍스트 fallback.
    if (await this.userMenuTrigger.count()) {
      await this.userMenuTrigger.click();
      const item = this.page.getByRole('menuitem', { name: /로그아웃/ });
      await item.click();
    } else {
      // mock 환경에서 사용자 메뉴 미구현 시 — 쿠키 삭제로 시뮬레이션.
      await this.page.context().clearCookies();
      await this.page.goto('/login');
    }
  }
}
