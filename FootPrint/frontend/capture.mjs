import { chromium } from '@playwright/test';

const BASE = 'http://localhost:3002';
const API  = 'http://localhost:8090/api/v1';
const OUT  = '/tmp/footprint-screenshots';

async function shot(page, name, waitMs = 800) {
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(waitMs);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  console.log(`  ✓ ${name}`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page    = await context.newPage();

  // 01. 로그인
  await page.goto(`${BASE}/login`);
  await shot(page, '01_login');

  // 02. 회원가입
  await page.goto(`${BASE}/signup`);
  await shot(page, '02_signup');

  // API 로그인 후 토큰 주입
  const res  = await page.request.post(`${API}/auth/login`, {
    data: { email: 'test@footprint.dev', password: 'Test1234!' }
  });
  const body = await res.json();
  const { accessToken, refreshToken } = body.data;

  await page.goto(BASE);
  await page.evaluate(({ at, rt }) => {
    localStorage.setItem('accessToken', at);
    localStorage.setItem('refreshToken', rt);
  }, { at: accessToken, rt: refreshToken });

  // 03. 장소 목록
  await page.goto(`${BASE}/places`);
  await shot(page, '03_places_list', 1500);

  // 04. 장소 상세
  await page.goto(`${BASE}/places/1`);
  await shot(page, '04_place_detail', 1200);

  // 05. 장소 등록 폼
  await page.goto(`${BASE}/places/new`);
  await shot(page, '05_place_new', 800);

  // 06. 지도
  await page.goto(`${BASE}/map`);
  await shot(page, '06_map', 2500);

  // 07. 통계
  await page.goto(`${BASE}/stats`);
  await shot(page, '07_stats', 1500);

  await browser.close();
  console.log('\n모든 스크린샷 완료 →', OUT);
}

main().catch(e => { console.error(e.message); process.exit(1); });
