// TradePilot 주문 API 부하 테스트 (k6)
//
// 시나리오:
//   - SIM 모드 주문 100 RPS 부하를 5분 유지.
//   - 응답 P95 < 500ms, 실패율 < 1% 목표.
//   - X-Idempotency-Key 는 매 요청 고유값 사용 (중복 차단 회피).
//
// 실행:
//   BASE_URL=https://staging.internal TOKEN=eyJ... \
//   k6 run k6_orders_burst.js
//
// 사전 조건:
//   - 사용자 jwt 토큰 (TOKEN 환경변수)
//   - 종목 005930 시드 데이터
//   - SIM 모드 사용자 (LIVE 사용 금지)

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TOKEN = __ENV.TOKEN || '';

export const options = {
  scenarios: {
    sim_burst: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 200,
      stages: [
        { target: 30,  duration: '30s' },   // 워밍업
        { target: 100, duration: '1m' },    // 100 RPS 도달
        { target: 100, duration: '3m' },    // 유지
        { target: 0,   duration: '30s' },   // 정리
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1500'],
    http_req_failed: ['rate<0.01'],
    'order_status_2xx': ['rate>0.99'],
  },
};

const successRate = new Rate('order_status_2xx');
const orderLatency = new Trend('order_latency_ms');

export default function () {
  const url = `${BASE_URL}/api/v1/orders`;
  const payload = JSON.stringify({
    code: '005930',
    side: 'BUY',
    qty: 1,
    order_type: 'MARKET',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TOKEN}`,
      'X-Trade-Mode': 'SIM',
      'X-Idempotency-Key': uuidv4(),
    },
    tags: { endpoint: 'POST /orders' },
  };

  const res = http.post(url, payload, params);
  orderLatency.add(res.timings.duration);

  const ok = check(res, {
    'status is 201/200/422': (r) => [200, 201, 422].includes(r.status),
    'no 5xx': (r) => r.status < 500,
    'response has body': (r) => r.body && r.body.length > 0,
  });
  successRate.add(ok);

  // 부하 분산을 위한 작은 jitter
  sleep(Math.random() * 0.05);
}

export function handleSummary(data) {
  return {
    'reports/k6_summary.json': JSON.stringify(data, null, 2),
    stdout: `\n=== 주문 API 부하 테스트 결과 ===
요청 수      : ${data.metrics.http_reqs.values.count}
실패율       : ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%
P95 지연(ms) : ${data.metrics.http_req_duration.values['p(95)'].toFixed(1)}
P99 지연(ms) : ${data.metrics.http_req_duration.values['p(99)'].toFixed(1)}
2xx 성공률   : ${(data.metrics.order_status_2xx.values.rate * 100).toFixed(2)}%
================================
`,
  };
}
