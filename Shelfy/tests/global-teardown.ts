import { FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  console.log('[GlobalTeardown] 테스트 완료 후 정리 작업');
}

export default globalTeardown;
