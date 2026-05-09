import { chromium, FullConfig } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8080/api/v1';

async function globalSetup(config: FullConfig) {
  console.log('[GlobalSetup] 테스트 환경 초기화 시작');
  console.log(`[GlobalSetup] BASE_URL: ${BASE_URL}`);
  console.log(`[GlobalSetup] API_URL: ${API_URL}`);

  // 환경 변수로 API URL 전달
  process.env.API_URL = API_URL;
  process.env.BASE_URL = BASE_URL;

  console.log('[GlobalSetup] 테스트 환경 초기화 완료');
}

export default globalSetup;
