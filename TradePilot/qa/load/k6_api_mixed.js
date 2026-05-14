// TradePilot 혼합 워크로드 부하 테스트 (k6)
//
// 시나리오:
//   - 실제 사용 패턴 모사: 로그인 → 대시보드 → 차트 → 시그널 → 주문
//   - 50 VU, 10분, ramp-up
//   - 각 VU 는 "1세션" 흐름을 반복하며 사용자 한 명의 행동을 모방.
//
// 실행:
//   BASE_URL=http://localhost:8000 \
//   TEST_USERNAME=user1 TEST_PASSWORD=pass1 \
//   k6 run qa/load/k6_api_mixed.js
//
// 사전 조건:
//   - 시드 사용자(SIM 모드) 계정
//   - 005930, 000660, 035420 등 종목 시드
//   - DB 연결, Redis 가동
//
// 합격 기준:
//   - 전체 P95 < 800ms (혼합 워크로드 기준; 단일 엔드포인트보다 느슨)
//   - 시나리오별 SLA 별도 체크
//   - 실패율 < 1%

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';
import { randomItem } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const USERNAME = __ENV.TEST_USERNAME || 'loadtest@example.com';
const PASSWORD = __ENV.TEST_PASSWORD || 'loadtest-pw';

const STOCKS = ['005930', '000660', '035420', '035720', '051910',
                '005380', '068270', '207940', '105560', '055550'];

// ---- 시나리오별 메트릭 ----
const loginLatency       = new Trend('flow_login_ms', true);
const dashboardLatency   = new Trend('flow_dashboard_ms', true);
const chartLatency       = new Trend('flow_chart_ms', true);
const signalLatency      = new Trend('flow_signal_ms', true);
const orderLatency       = new Trend('flow_order_ms', true);

const loginSuccess     = new Rate('flow_login_ok');
const dashboardSuccess = new Rate('flow_dashboard_ok');
const chartSuccess     = new Rate('flow_chart_ok');
const signalSuccess    = new Rate('flow_signal_ok');
const orderSuccess     = new Rate('flow_order_ok');

const sessionsCompleted = new Counter('sessions_completed');

export const options = {
  scenarios: {
    mixed_session: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m',  target: 20 },   // ramp-up
        { duration: '1m',  target: 50 },   // 목표 도달
        { duration: '7m',  target: 50 },   // 유지 (총 10분 중 7분)
        { duration: '1m',  target: 0  },   // ramp-down
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    'http_req_failed':       ['rate<0.01'],
    'http_req_duration':     ['p(95)<800', 'p(99)<2000'],
    'flow_login_ms':         ['p(95)<600'],
    'flow_dashboard_ms':     ['p(95)<500'],
    'flow_chart_ms':         ['p(95)<700'],
    'flow_signal_ms':        ['p(95)<500'],
    'flow_order_ms':         ['p(95)<500'],
    'flow_login_ok':         ['rate>0.99'],
    'flow_order_ok':         ['rate>0.99'],
  },
};

function jsonPost(url, body, headers) {
  return http.post(url, JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json', ...(headers || {}) },
  });
}

function authGet(url, token, tag) {
  return http.get(url, {
    headers: { 'Authorization': `Bearer ${token}` },
    tags: { endpoint: tag },
  });
}

export default function () {
  let token = null;
  const code = randomItem(STOCKS);

  // 1) 로그인
  group('1_login', () => {
    const res = jsonPost(`${BASE_URL}/api/v1/auth/login`,
      { email: USERNAME, password: PASSWORD });
    loginLatency.add(res.timings.duration);
    const ok = check(res, {
      'login 200': (r) => r.status === 200,
      'access token present': (r) => r.json('access_token') !== '',
    });
    loginSuccess.add(ok);
    if (ok) token = res.json('access_token');
  });
  if (!token) {
    // 인증 실패 시 세션 중단
    sleep(1);
    return;
  }

  // 2) 대시보드 (메인 화면)
  group('2_dashboard', () => {
    const res = authGet(`${BASE_URL}/api/v1/reports/daily-summary`, token, 'GET /reports/daily-summary');
    dashboardLatency.add(res.timings.duration);
    dashboardSuccess.add(check(res, {
      'dashboard 200/404': (r) => r.status === 200 || r.status === 404,
    }));
  });

  // 3) 차트 조회
  group('3_chart', () => {
    const res = authGet(`${BASE_URL}/api/v1/chart/${code}?interval=D`, token, 'GET /chart');
    chartLatency.add(res.timings.duration);
    chartSuccess.add(check(res, {
      'chart 200/404': (r) => r.status === 200 || r.status === 404,
    }));
  });

  // 4) 시그널 조회
  group('4_signals', () => {
    const res = authGet(`${BASE_URL}/api/v1/signals?status=ACTIVE&page=1&size=10`, token, 'GET /signals');
    signalLatency.add(res.timings.duration);
    signalSuccess.add(check(res, {
      'signal 200': (r) => r.status === 200 || r.status === 404,
    }));
  });

  // 5) 주문 (SIM 모드)
  group('5_order', () => {
    const res = http.post(`${BASE_URL}/api/v1/orders`,
      JSON.stringify({ code, side: 'BUY', qty: 1, order_type: 'MARKET' }),
      {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-Trade-Mode': 'SIM',
          'X-Idempotency-Key': uuidv4(),
        },
        tags: { endpoint: 'POST /orders' },
      });
    orderLatency.add(res.timings.duration);
    orderSuccess.add(check(res, {
      'order 200/201/422': (r) => [200, 201, 422].includes(r.status),
      'no 5xx': (r) => r.status < 500,
    }));
  });

  sessionsCompleted.add(1);
  // 사용자가 화면 보고 잠시 대기하는 패턴
  sleep(1 + Math.random() * 2);
}

export function handleSummary(data) {
  const m = data.metrics;
  const get = (k, sub) => (m[k] && m[k].values && m[k].values[sub]) || 0;
  return {
    'reports/k6_api_mixed_summary.json': JSON.stringify(data, null, 2),
    stdout: `
=== 혼합 워크로드 부하 결과 ===
완료 세션 수            : ${get('sessions_completed', 'count')}
전체 P95 (ms)           : ${get('http_req_duration', 'p(95)').toFixed(1)}
전체 P99 (ms)           : ${get('http_req_duration', 'p(99)').toFixed(1)}
실패율                  : ${(get('http_req_failed', 'rate') * 100).toFixed(2)}%
로그인 P95 (ms)         : ${get('flow_login_ms', 'p(95)').toFixed(1)}
대시보드 P95 (ms)       : ${get('flow_dashboard_ms', 'p(95)').toFixed(1)}
차트 P95 (ms)           : ${get('flow_chart_ms', 'p(95)').toFixed(1)}
시그널 P95 (ms)         : ${get('flow_signal_ms', 'p(95)').toFixed(1)}
주문 P95 (ms)           : ${get('flow_order_ms', 'p(95)').toFixed(1)}
주문 성공률             : ${(get('flow_order_ok', 'rate') * 100).toFixed(2)}%
================================
`,
  };
}
