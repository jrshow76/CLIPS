/*
 * TradePilot Service Worker
 * ----------------------------------------------------------
 * 책임:
 *   1) 앱 셸 precache (오프라인 진입 보장)
 *   2) 런타임 캐시 전략 (정적 자산 / API / 이미지 별 분리)
 *   3) Web Push 이벤트 수신 → showNotification
 *   4) 알림 클릭 → 해당 페이지 포커스/오픈
 *   5) skipWaiting + clients.claim 으로 즉시 활성화
 *
 * 캐시 버전:
 *   - 빌드마다 SW_VERSION 을 갱신해 구 캐시를 폐기한다 (deploy script 또는 수동).
 *
 * 캐시 전략 요약:
 *   - 앱 셸 / HTML: NetworkFirst (실패 시 offline.html)
 *   - /_next/static, /icons: CacheFirst (장기, 7일)
 *   - 이미지: CacheFirst (7일)
 *   - API GET (/api/v1/...): StaleWhileRevalidate (5분 TTL) — 인증 토큰이 붙는 요청은 캐시하지 않음
 *
 * iOS Safari 16.4+ 만 Web Push 지원. 그 미만은 SW 등록만 동작 (오프라인 셸).
 */

const SW_VERSION = 'tp-sw-v1.0.0';
const APP_SHELL_CACHE = `${SW_VERSION}-shell`;
const RUNTIME_STATIC_CACHE = `${SW_VERSION}-static`;
const RUNTIME_IMAGE_CACHE = `${SW_VERSION}-images`;
const RUNTIME_API_CACHE = `${SW_VERSION}-api`;

const APP_SHELL = [
  '/',
  '/dashboard',
  '/offline.html',
  '/manifest.webmanifest',
  '/icons/icon-192-placeholder.svg',
  '/icons/icon-512-placeholder.svg',
];

const API_CACHE_TTL_MS = 5 * 60 * 1000; // 5분
const IMAGE_CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7일

// ============================================================
// install: 앱 셸 precache
// ============================================================
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(APP_SHELL_CACHE)
      .then((cache) => cache.addAll(APP_SHELL).catch((err) => {
        // 일부 자산 누락 시에도 SW 설치는 진행
        // (예: dev 모드에서 /dashboard 미생성)
        console.warn('[sw] app shell precache partial fail', err);
      }))
      .then(() => self.skipWaiting()),
  );
});

// ============================================================
// activate: 구 캐시 정리
// ============================================================
self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((k) => !k.startsWith(SW_VERSION))
          .map((k) => caches.delete(k)),
      );
      await self.clients.claim();
    })(),
  );
});

// ============================================================
// fetch: 요청 경로별 캐시 전략 라우팅
// ============================================================
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return; // POST/PUT/DELETE 는 항상 네트워크
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // 외부 자원은 패스

  // 1) Next.js 정적 빌드 자산 → CacheFirst
  if (url.pathname.startsWith('/_next/static/') || url.pathname.startsWith('/icons/')) {
    event.respondWith(cacheFirst(req, RUNTIME_STATIC_CACHE));
    return;
  }

  // 2) 이미지 자원 → CacheFirst (만료 7일)
  if (/\.(png|jpg|jpeg|webp|gif|svg|ico)$/i.test(url.pathname)) {
    event.respondWith(cacheFirstWithTTL(req, RUNTIME_IMAGE_CACHE, IMAGE_CACHE_TTL_MS));
    return;
  }

  // 3) API GET 요청 → StaleWhileRevalidate (Authorization 헤더 있어도 동일 정책, 사용자 토큰별 cache key 가 다르므로 안전)
  // 단, /auth/ 와 /notifications/push/ 는 캐시 금지 (민감 / 가변)
  if (url.pathname.startsWith('/api/v1/')) {
    if (
      url.pathname.startsWith('/api/v1/auth/') ||
      url.pathname.startsWith('/api/v1/notifications/push/')
    ) {
      return; // 네트워크 직통
    }
    event.respondWith(staleWhileRevalidate(req, RUNTIME_API_CACHE, API_CACHE_TTL_MS));
    return;
  }

  // 4) navigation (HTML 페이지) → NetworkFirst, 실패 시 offline.html
  if (req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html')) {
    event.respondWith(networkFirstHtml(req));
    return;
  }

  // 5) 그 외 → 기본 (네트워크 우선, 실패 시 캐시)
  event.respondWith(networkFirst(req, RUNTIME_STATIC_CACHE));
});

// ============================================================
// 캐시 전략 유틸
// ============================================================
async function cacheFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);
  if (cached) return cached;
  try {
    const res = await fetch(req);
    if (res && res.status === 200) cache.put(req, res.clone());
    return res;
  } catch (e) {
    return new Response('', { status: 504, statusText: 'Offline' });
  }
}

async function cacheFirstWithTTL(req, cacheName, ttlMs) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);
  if (cached) {
    const dateHeader = cached.headers.get('sw-cached-at');
    const cachedAt = dateHeader ? Number(dateHeader) : 0;
    if (Date.now() - cachedAt < ttlMs) return cached;
  }
  try {
    const res = await fetch(req);
    if (res && res.status === 200) {
      const headers = new Headers(res.headers);
      headers.set('sw-cached-at', String(Date.now()));
      const body = await res.clone().blob();
      const wrapped = new Response(body, {
        status: res.status,
        statusText: res.statusText,
        headers,
      });
      cache.put(req, wrapped);
    }
    return res;
  } catch (e) {
    if (cached) return cached; // 만료되었더라도 오프라인 시 폴백
    return new Response('', { status: 504, statusText: 'Offline' });
  }
}

async function networkFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const res = await fetch(req);
    if (res && res.status === 200) cache.put(req, res.clone());
    return res;
  } catch (e) {
    const cached = await cache.match(req);
    if (cached) return cached;
    throw e;
  }
}

async function networkFirstHtml(req) {
  try {
    const res = await fetch(req);
    return res;
  } catch (e) {
    const cache = await caches.open(APP_SHELL_CACHE);
    const cached = await cache.match(req);
    if (cached) return cached;
    const offline = await cache.match('/offline.html');
    if (offline) return offline;
    return new Response('<h1>오프라인입니다</h1>', {
      status: 503,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
  }
}

async function staleWhileRevalidate(req, cacheName, ttlMs) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);
  const fetchPromise = fetch(req)
    .then((res) => {
      if (res && res.status === 200) {
        const headers = new Headers(res.headers);
        headers.set('sw-cached-at', String(Date.now()));
        res.clone().blob().then((body) => {
          cache.put(req, new Response(body, { status: res.status, statusText: res.statusText, headers }));
        });
      }
      return res;
    })
    .catch(() => null);

  if (cached) {
    const dateHeader = cached.headers.get('sw-cached-at');
    const cachedAt = dateHeader ? Number(dateHeader) : 0;
    const isFresh = Date.now() - cachedAt < ttlMs;
    if (isFresh) {
      // 백그라운드 갱신만, 즉시 캐시 반환
      fetchPromise.catch(() => {});
      return cached;
    }
  }

  const network = await fetchPromise;
  if (network) return network;
  if (cached) return cached;
  return new Response(
    JSON.stringify({ success: false, error: { code: 'E_OFFLINE', message: '오프라인 상태입니다.' } }),
    { status: 504, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
  );
}

// ============================================================
// Web Push: push 이벤트
// ============================================================
self.addEventListener('push', (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (_e) {
    try {
      payload = { title: 'TradePilot', body: event.data ? event.data.text() : '' };
    } catch (_e2) {
      payload = { title: 'TradePilot', body: '새 알림' };
    }
  }

  const title = payload.title || 'TradePilot';
  const severity = (payload.severity || 'INFO').toUpperCase();
  const isCritical = severity === 'CRITICAL';

  const options = {
    body: payload.body || '',
    icon: payload.icon || '/icons/icon-192-placeholder.svg',
    badge: payload.badge || '/icons/icon-192-placeholder.svg',
    tag: payload.tag || `tp-${payload.event_type || 'general'}`,
    renotify: !!payload.renotify || isCritical,
    requireInteraction: isCritical,
    silent: false,
    timestamp: Date.now(),
    data: {
      url: payload.url || resolveUrlByEventType(payload.event_type, payload.payload),
      event_type: payload.event_type || null,
      notification_id: payload.notification_id || null,
      severity,
    },
    actions: buildActions(payload),
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

function buildActions(payload) {
  // iOS Safari 16.4+ 는 actions 무시. Android Chrome 에서만 표시.
  const actions = [];
  if (payload.event_type === 'SIGNAL' && payload.payload?.stock_code) {
    actions.push({ action: 'view_chart', title: '차트 보기' });
  }
  if (payload.event_type === 'ORDER_FILLED') {
    actions.push({ action: 'view_order', title: '주문 보기' });
  }
  actions.push({ action: 'dismiss', title: '닫기' });
  return actions;
}

function resolveUrlByEventType(eventType, payload) {
  const code = payload?.stock_code;
  switch (eventType) {
    case 'SIGNAL':
      return code ? `/chart/${code}` : '/signals';
    case 'ORDER_FILLED':
      return '/auto-trading/orders';
    case 'KILL_SWITCH':
      return '/auto-trading';
    case 'SECURITY':
      return '/settings';
    case 'DAILY_REPORT':
      return '/report';
    default:
      return '/notifications';
  }
}

// ============================================================
// 알림 클릭 → 해당 페이지로 이동/포커스
// ============================================================
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  const targetUrl =
    (event.action === 'view_chart' || event.action === 'view_order')
      ? event.notification.data?.url || '/notifications'
      : event.notification.data?.url || '/notifications';

  event.waitUntil(
    (async () => {
      const allClients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      // 동일 앱이 이미 열려 있으면 포커스 + 라우팅 메시지 전송
      for (const client of allClients) {
        const url = new URL(client.url);
        if (url.origin === self.location.origin) {
          client.postMessage({ type: 'NAVIGATE', url: targetUrl });
          await client.focus();
          return;
        }
      }
      // 없으면 신규 윈도우 오픈
      await self.clients.openWindow(targetUrl);
    })(),
  );
});

// ============================================================
// 푸시 구독 만료 처리: pushsubscriptionchange
// ----------------------------------------------------------
// 일부 브라우저에서 구독이 만료되면 발생. 새 구독을 만들어
// 클라이언트로 알린다 (실제 백엔드 재등록은 클라이언트가 수행).
// ============================================================
self.addEventListener('pushsubscriptionchange', (event) => {
  event.waitUntil(
    (async () => {
      const clientsList = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const client of clientsList) {
        client.postMessage({ type: 'PUSH_SUBSCRIPTION_CHANGED' });
      }
    })(),
  );
});

// ============================================================
// 메시지 채널 (앱 → SW): 캐시 정리, 즉시 활성화 등
// ============================================================
self.addEventListener('message', (event) => {
  const data = event.data || {};
  if (data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  } else if (data.type === 'CLEAR_CACHES') {
    event.waitUntil(
      (async () => {
        const keys = await caches.keys();
        await Promise.all(keys.map((k) => caches.delete(k)));
        if (event.ports && event.ports[0]) {
          event.ports[0].postMessage({ ok: true });
        }
      })(),
    );
  }
});
