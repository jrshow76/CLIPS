// TradePilot 시그널 조회 API 부하 테스트 (k6)
//
// 시나리오:
//   - GET /api/v1/signals 200 RPS, 5분 유지.
//   - 캐시 적중 가능성이 큰 GET 엔드포인트 (Redis 캐싱 권장 대상) 검증.
//   - 임의의 status/페이지 조합으로 캐시 히트율 동시 측정.
//
// 실행:
//   BASE_URL=http://localhost:8000 TOKEN=eyJ... \
//   k6 run qa/load/k6_signals_burst.js
//
// 합격 기준 (SLA):
//   - P95 < 300ms (조회 SLA)
//   - P99 < 800ms
//   - 실패율 < 1%
//   - 200 응답 비율 > 99%

import http from 'k6/http';
import { check } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomItem, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TOKEN = __ENV.TOKEN || '';

const STATUSES = ['ACTIVE', 'CLOSED', 'PENDING'];
const STRATEGIES = ['', 'momentum_v2', 'mean_reversion', 'breakout_swing'];

const sigLatency = new Trend('signals_latency_ms', true);
const sig2xx = new Rate('signals_status_2xx');
const sigCacheHits = new Counter('signals_cache_hit_estimate'); // p50<50ms 기준 추정

export const options = {
  scenarios: {
    signals_burst: {
      executor: 'ramping-arrival-rate',
      startRate: 20,
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 400,
      stages: [
        { target: 50,  duration: '30s' },
        { target: 200, duration: '1m' },
        { target: 200, duration: '3m' },
        { target: 0,   duration: '30s' },
      ],
    },
  },
  thresholds: {
    'http_req_duration':   ['p(95)<300', 'p(99)<800'],
    'http_req_failed':     ['rate<0.01'],
    'signals_status_2xx':  ['rate>0.99'],
  },
};

export default function () {
  const status = randomItem(STATUSES);
  const strategy = randomItem(STRATEGIES);
  const page = randomIntBetween(1, 5);
  const size = randomItem([10, 20, 50]);

  let url = `${BASE_URL}/api/v1/signals?status=${status}&page=${page}&size=${size}`;
  if (strategy) url += `&strategy=${encodeURIComponent(strategy)}`;

  const res = http.get(url, {
    headers: TOKEN ? { 'Authorization': `Bearer ${TOKEN}` } : {},
    tags: { endpoint: 'GET /signals' },
  });

  sigLatency.add(res.timings.duration);
  const ok = check(res, {
    'status 200/401/404': (r) => [200, 401, 404].includes(r.status),
    'no 5xx': (r) => r.status < 500,
  });
  sig2xx.add(ok && res.status === 200);

  // 캐시 히트 추정: 50ms 이하면 Redis 또는 메모리 캐시 적중 가능성 큼
  if (res.timings.duration < 50) sigCacheHits.add(1);
}

export function handleSummary(data) {
  const m = data.metrics;
  const get = (k, sub) => (m[k] && m[k].values && m[k].values[sub]) || 0;
  return {
    'reports/k6_signals_summary.json': JSON.stringify(data, null, 2),
    stdout: `
=== 시그널 조회 부하 결과 ===
요청 수                  : ${get('http_reqs', 'count')}
실패율                   : ${(get('http_req_failed', 'rate') * 100).toFixed(2)}%
P50 (ms)                 : ${get('http_req_duration', 'p(50)').toFixed(1)}
P95 (ms)                 : ${get('http_req_duration', 'p(95)').toFixed(1)}
P99 (ms)                 : ${get('http_req_duration', 'p(99)').toFixed(1)}
2xx 비율                 : ${(get('signals_status_2xx', 'rate') * 100).toFixed(2)}%
캐시 히트 추정 (P<50ms)  : ${get('signals_cache_hit_estimate', 'count')}
==============================
`,
  };
}
