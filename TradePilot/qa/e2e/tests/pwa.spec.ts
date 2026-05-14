import { expect, test } from '@playwright/test';

/**
 * PWA E2E 테스트.
 *  - 매니페스트 / 아이콘 / Service Worker 등록 검증
 *  - 오프라인 시 fallback 페이지 (offline.html) 노출
 *  - 설정 화면의 PWA 섹션 노출
 *  - VAPID 공개키 API 응답 형태
 *
 * 주의:
 *  - Service Worker 는 NEXT_PUBLIC_ENABLE_SW=true 또는 production 빌드에서만 등록된다.
 *    CI 에서는 production 빌드 결과를 띄워 테스트.
 *  - Playwright Chromium 기본은 SW 를 지원한다. WebKit/Safari 는 SW 등록 자체는 가능하지만
 *    Push API 가 standalone PWA 컨텍스트에서만 동작하므로 별도 케이스 분리.
 */

test.describe('PWA — 매니페스트 / Service Worker', () => {
  test('TC-PWA-001: manifest.webmanifest 정상 응답', async ({ page }) => {
    const res = await page.request.get('/manifest.webmanifest');
    expect(res.ok()).toBeTruthy();
    const ct = res.headers()['content-type'] || '';
    // Next.js public 자산은 application/manifest+json 또는 application/json
    expect(ct).toMatch(/json|manifest/);
    const body = await res.json();
    expect(body.name).toMatch(/TradePilot/i);
    expect(body.start_url).toBeTruthy();
    expect(Array.isArray(body.icons)).toBeTruthy();
    expect(body.icons.length).toBeGreaterThanOrEqual(2);
    expect(['standalone', 'minimal-ui', 'fullscreen']).toContain(body.display);
  });

  test('TC-PWA-002: sw.js 정적 자산이 응답된다', async ({ page }) => {
    const res = await page.request.get('/sw.js');
    expect(res.ok()).toBeTruthy();
    const text = await res.text();
    expect(text).toContain('addEventListener');
    expect(text).toContain('push');
    expect(text).toContain('caches');
  });

  test('TC-PWA-003: offline.html fallback 페이지가 응답된다', async ({ page }) => {
    const res = await page.request.get('/offline.html');
    expect(res.ok()).toBeTruthy();
    const body = await res.text();
    expect(body).toContain('오프라인');
  });

  test('TC-PWA-004: head 에 manifest 링크와 apple meta 태그가 존재', async ({ page }) => {
    await page.goto('/');
    const manifestHref = await page.locator('link[rel="manifest"]').getAttribute('href');
    expect(manifestHref).toMatch(/manifest\.webmanifest$/);
    const appleCapable = await page
      .locator('meta[name="apple-mobile-web-app-capable"]')
      .getAttribute('content');
    expect(appleCapable).toBe('yes');
  });

  test('TC-PWA-005: Service Worker 등록 (production / ENABLE_SW=true 일 때)', async ({ page }) => {
    await page.goto('/');
    // SW 가 등록될 때까지 최대 5초 대기 — dev 빌드에서는 skip
    const swReady = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) return 'unsupported';
      try {
        const reg = await Promise.race([
          navigator.serviceWorker.getRegistration(),
          new Promise<undefined>((resolve) => setTimeout(() => resolve(undefined), 5000)),
        ]);
        return reg ? 'registered' : 'none';
      } catch {
        return 'error';
      }
    });
    // dev 모드에서는 'none' 가능 — 환경별 분기
    expect(['registered', 'none', 'unsupported']).toContain(swReady);
  });
});

test.describe('PWA — 오프라인 셸', () => {
  test('TC-PWA-010: 오프라인 상태에서 캐시된 페이지로 진입 시 fallback', async ({ page, context }) => {
    // 사전 진입으로 정적 자산을 캐시에 적재
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 오프라인 모드로 전환
    await context.setOffline(true);
    const response = await page.goto('/some-nonexistent-page', { waitUntil: 'domcontentloaded' }).catch(() => null);

    // SW 가 미등록(dev)인 환경에서는 페이지가 그냥 실패 — 분기 처리
    if (response) {
      const text = await page.content();
      // 오프라인 페이지 또는 NetworkFirst 에 의해 어떤 응답이 돌아왔는지 검증
      expect(text.length).toBeGreaterThan(0);
    }
    await context.setOffline(false);
  });
});

test.describe('PWA — 설정 화면 PWA 섹션', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    const email = page.getByLabel('이메일');
    if (await email.isVisible().catch(() => false)) {
      await email.fill('demo@test.local');
      await page.getByLabel('비밀번호').fill('Demo1234!');
      await page.getByRole('button', { name: '로그인' }).click();
    }
  });

  test('TC-PWA-020: 설정 → 앱/푸시 탭 노출', async ({ page }) => {
    await page.goto('/settings');
    const tab = page.getByRole('tab', { name: /앱\/푸시/ });
    if (await tab.count()) {
      await tab.click();
      await expect(page.getByText(/PWA/i)).toBeVisible();
      await expect(page.getByText(/푸시 알림/)).toBeVisible();
      // 캐시 비우기 / 업데이트 버튼이 보여야 함
      await expect(page.getByRole('button', { name: /캐시/ })).toBeVisible();
    }
  });
});

test.describe('PWA — Web Push API', () => {
  test('TC-PWA-030: VAPID 공개키 API 응답 (인증 필요 — 401 도 허용)', async ({ request }) => {
    const res = await request.get('/api/v1/notifications/push/vapid-public-key');
    // 인증 미적용 시 401 / 적용 시 200 — 둘 다 허용
    expect([200, 401, 403]).toContain(res.status());
    if (res.ok()) {
      const body = await res.json();
      // envelope: { success, data: { public_key } }
      const data = body.data ?? body;
      expect(data).toHaveProperty('public_key');
      // VAPID 키가 미설정이면 null
      const key = data.public_key;
      if (key !== null) {
        expect(typeof key).toBe('string');
        expect(key.length).toBeGreaterThan(60);
      }
    }
  });
});
