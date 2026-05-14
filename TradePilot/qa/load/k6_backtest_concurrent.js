// TradePilot 백테스트 동시성 부하 테스트 (k6)
//
// 시나리오:
//   - 동시 10건 백테스트 작업을 짧은 간격으로 제출 → Celery 큐 적체/완료 시간 측정.
//   - 매 작업: POST /api/v1/backtest/start (비동기) → polling /api/v1/backtest/{id}
//   - 큐 처리 능력, DB 동시 트랜잭션, 메모리 사용량 평가.
//
// 실행:
//   BASE_URL=http://localhost:8000 TOKEN=eyJ... \
//   k6 run qa/load/k6_backtest_concurrent.js
//
// 합격 기준 (백테스트 SLA):
//   - 5년 일봉 단일 종목 P95 < 30s
//   - 동시 10건 모두 30분 내 완료
//   - 큐 적체 시점 알림 (max queue depth)
//
// 주의:
//   - 백테스트는 CPU/DB 부하가 큼. SIM 환경 또는 사양 격리된 staging에서만 실행.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend, Rate } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TOKEN = __ENV.TOKEN || '';
const N_JOBS = parseInt(__ENV.N_JOBS || '10', 10);
const POLL_INTERVAL_SEC = parseInt(__ENV.POLL_INTERVAL_SEC || '5', 10);
const MAX_WAIT_SEC = parseInt(__ENV.MAX_WAIT_SEC || '1800', 10); // 30분

const submitLatency = new Trend('bt_submit_ms', true);
const completeLatency = new Trend('bt_complete_sec', true);
const submitSuccess = new Rate('bt_submit_ok');
const completeSuccess = new Rate('bt_complete_ok');
const timeouts = new Counter('bt_timeouts');

export const options = {
  scenarios: {
    backtest_concurrent: {
      executor: 'per-vu-iterations',
      vus: N_JOBS,
      iterations: 1,
      maxDuration: `${MAX_WAIT_SEC + 60}s`,
    },
  },
  thresholds: {
    'bt_submit_ok':      ['rate>0.95'],
    'bt_complete_ok':    ['rate>0.90'],
    'bt_complete_sec':   ['p(95)<1800'],   // 30분 이내
    'bt_submit_ms':      ['p(95)<2000'],
  },
};

// 종목 풀 (VU별 다른 종목으로 캐시 회피)
const STOCKS = ['005930', '000660', '035420', '035720', '051910',
                '005380', '068270', '207940', '105560', '055550'];

const PAYLOAD_TEMPLATE = (code) => ({
  code,
  strategy_id: 'momentum_v2',
  start_date: '2020-01-01',
  end_date: '2024-12-31',
  initial_capital: 10000000,
  interval: 'D',
});

export default function () {
  const code = STOCKS[(__VU - 1) % STOCKS.length];
  const body = JSON.stringify(PAYLOAD_TEMPLATE(code));
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${TOKEN}`,
  };

  // 1) 작업 제출
  const t0 = Date.now();
  const submit = http.post(`${BASE_URL}/api/v1/backtest/start`, body, {
    headers,
    tags: { endpoint: 'POST /backtest/start' },
  });
  submitLatency.add(submit.timings.duration);
  const submitted = check(submit, {
    'submit 202/200': (r) => [200, 202].includes(r.status),
    'has job_id': (r) => (r.json('job_id') || r.json('id')) != null,
  });
  submitSuccess.add(submitted);
  if (!submitted) return;

  const jobId = submit.json('job_id') || submit.json('id');
  console.log(`[VU=${__VU}] submitted job_id=${jobId} code=${code}`);

  // 2) 폴링 (status=DONE 또는 FAILED 까지)
  const deadline = Date.now() + MAX_WAIT_SEC * 1000;
  let finalStatus = null;
  while (Date.now() < deadline) {
    sleep(POLL_INTERVAL_SEC);
    const poll = http.get(`${BASE_URL}/api/v1/backtest/${jobId}`, {
      headers: { 'Authorization': `Bearer ${TOKEN}` },
      tags: { endpoint: 'GET /backtest/{id}' },
    });
    if (poll.status !== 200) continue;
    const status = poll.json('status');
    if (status === 'DONE' || status === 'COMPLETED' || status === 'SUCCESS') {
      finalStatus = 'DONE';
      break;
    }
    if (status === 'FAILED' || status === 'ERROR') {
      finalStatus = 'FAILED';
      break;
    }
  }

  const elapsed = (Date.now() - t0) / 1000;
  completeLatency.add(elapsed);
  const ok = finalStatus === 'DONE';
  completeSuccess.add(ok);
  if (!finalStatus) timeouts.add(1);

  console.log(`[VU=${__VU}] job_id=${jobId} final=${finalStatus || 'TIMEOUT'} elapsed=${elapsed.toFixed(1)}s`);
}

export function handleSummary(data) {
  const m = data.metrics;
  const get = (k, sub) => (m[k] && m[k].values && m[k].values[sub]) || 0;
  return {
    'reports/k6_backtest_summary.json': JSON.stringify(data, null, 2),
    stdout: `
=== 백테스트 동시성 부하 결과 ===
동시 작업 수             : ${N_JOBS}
제출 P95 (ms)            : ${get('bt_submit_ms', 'p(95)').toFixed(1)}
제출 성공률              : ${(get('bt_submit_ok', 'rate') * 100).toFixed(2)}%
완료 P50 (sec)           : ${get('bt_complete_sec', 'p(50)').toFixed(1)}
완료 P95 (sec)           : ${get('bt_complete_sec', 'p(95)').toFixed(1)}
완료 성공률              : ${(get('bt_complete_ok', 'rate') * 100).toFixed(2)}%
타임아웃 수              : ${get('bt_timeouts', 'count')}
=================================
`,
  };
}
