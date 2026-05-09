import { defineConfig, devices } from '@playwright/test';

/**
 * 발자국 (Foot-Print) Playwright E2E 테스트 설정
 * 참조: https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/*.spec.ts',

  /* 전체 테스트 제한 시간: 2분 */
  timeout: 120_000,

  /* 단일 테스트 expect 제한 시간: 10초 */
  expect: {
    timeout: 10_000,
  },

  /* CI 환경에서는 병렬 실행 비활성화 */
  fullyParallel: !process.env.CI,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],

  use: {
    baseURL: 'http://localhost:3000',

    /* 모든 테스트 실패 시 스크린샷 자동 저장 */
    screenshot: 'only-on-failure',

    /* 실패한 테스트 비디오 저장 */
    video: 'retain-on-failure',

    /* 실패 시 trace 저장 (재현 분석용) */
    trace: 'retain-on-failure',

    /* 브라우저 타임아웃 */
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  /* 스크린샷/비디오 저장 경로 */
  outputDir: 'test-results',

  projects: [
    /* 전역 setup: 테스트 사용자 생성 및 로그인 상태 저장 */
    {
      name: 'setup',
      testMatch: '**/global.setup.ts',
    },

    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'tests/e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'tests/e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        storageState: 'tests/e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },

    /* 모바일 반응형 테스트 (Chromium) */
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
        storageState: 'tests/e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],

  /* 테스트 실행 전 개발 서버 자동 시작 (로컬 환경) */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
