/**
 * Playwright E2E 설정 — Tulip+ 프론트엔드 모노레포 루트
 * ---------------------------------------------------------------
 * Sprint 1-D / QA (Phase 1-D)
 *
 * - admin 앱: http://localhost:3000
 * - opac  앱: http://localhost:3001
 *
 * 두 앱을 동시에 다루기 위해 단일 `tests/` 디렉토리에 spec을 모으고,
 * 프로젝트(project)로 baseURL과 storageState를 구분한다.
 *
 * 실행 모드:
 *   1) mock 모드 (기본)  — NEXT_PUBLIC_USE_MOCK=true, 백엔드 불필요
 *      pnpm exec playwright test
 *
 *   2) 실 모드          — 백엔드 + Keycloak 가동된 상태
 *      E2E_MODE=live pnpm exec playwright test
 *
 *   3) CI 모드          — webServer가 admin/opac을 자동 빌드/기동
 *      CI=true pnpm exec playwright test
 */
import { defineConfig, devices } from '@playwright/test';

const IS_CI = !!process.env.CI;
const MODE = (process.env.E2E_MODE ?? 'mock') as 'mock' | 'live';

const ADMIN_BASE_URL = process.env.E2E_ADMIN_BASE_URL ?? 'http://localhost:3000';
const OPAC_BASE_URL = process.env.E2E_OPAC_BASE_URL ?? 'http://localhost:3001';

export default defineConfig({
  testDir: './tests/e2e',
  // 결과·리포트는 모두 tests/e2e-results/에 모은다 (gitignore 대상)
  outputDir: './tests/e2e-results/artifacts',

  /** 빠른 실패 — CI에서 정확한 picking을 위해. */
  fullyParallel: true,
  forbidOnly: IS_CI,
  retries: IS_CI ? 2 : 0,
  workers: IS_CI ? 2 : 2,
  timeout: 60_000,
  expect: { timeout: 10_000 },

  reporter: [
    ['list'],
    ['html', { outputFolder: './tests/e2e-results/html', open: 'never' }],
    [
      'junit',
      { outputFile: './tests/e2e-results/junit/results.xml' },
    ],
  ],

  use: {
    /** 기본 baseURL은 admin. opac 전용 테스트는 page.goto에 OPAC_BASE_URL을 명시 사용. */
    baseURL: ADMIN_BASE_URL,
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    /** 한국어 로케일 기본 — 테스트 시나리오와 일관성을 위해. */
    locale: 'ko-KR',
    timezoneId: 'Asia/Seoul',
    /** 한글 시나리오에 적합한 폰트 렌더링을 위해. */
    viewport: { width: 1366, height: 800 },
  },

  /**
   * 프로젝트 분리
   *  - admin-chromium / opac-chromium 기본
   *  - 옵션으로 firefox / webkit 활성화 (PLAYWRIGHT_BROWSERS=all)
   */
  projects: [
    {
      name: 'admin-chromium',
      testMatch: /(auth|members|libraries|rls)\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: ADMIN_BASE_URL,
      },
    },
    {
      name: 'opac-chromium',
      testMatch: /opac\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: OPAC_BASE_URL,
      },
    },
    ...(process.env.PLAYWRIGHT_BROWSERS === 'all'
      ? [
          {
            name: 'admin-firefox',
            testMatch: /(auth|members|libraries)\.spec\.ts/,
            use: { ...devices['Desktop Firefox'], baseURL: ADMIN_BASE_URL },
          },
          {
            name: 'admin-webkit',
            testMatch: /(auth|members|libraries)\.spec\.ts/,
            use: { ...devices['Desktop Safari'], baseURL: ADMIN_BASE_URL },
          },
        ]
      : []),
  ],

  /**
   * CI 또는 webServer 자동 기동 모드일 때 admin/opac을 함께 띄운다.
   * 로컬 개발 시에는 `pnpm dev`로 이미 띄운 상태를 권장하므로 webServer를 비활성.
   */
  webServer:
    IS_CI || process.env.E2E_USE_WEBSERVER === 'true'
      ? [
          {
            command: 'pnpm -F @tulip/admin start',
            url: ADMIN_BASE_URL,
            reuseExistingServer: !IS_CI,
            timeout: 180_000,
            env: {
              NODE_ENV: 'production',
              NEXT_PUBLIC_USE_MOCK: MODE === 'live' ? 'false' : 'true',
              NEXT_PUBLIC_AUTH_COOKIE_NAME: 'tulip_refresh',
            },
          },
          {
            command: 'pnpm -F @tulip/opac start',
            url: OPAC_BASE_URL,
            reuseExistingServer: !IS_CI,
            timeout: 180_000,
            env: {
              NODE_ENV: 'production',
              NEXT_PUBLIC_USE_MOCK: MODE === 'live' ? 'false' : 'true',
              NEXT_PUBLIC_AUTH_COOKIE_NAME: 'tulip_refresh',
            },
          },
        ]
      : undefined,
});
