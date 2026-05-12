/**
 * k6 부하 — 대시보드 KPI 조회
 * Phase 1-D 목표: 30 RPS, P99 < 400ms
 *
 * 실행: k6 run dashboard.js
 *
 * 백엔드 통계 API는 Phase 2 도입 예정 — 본 스크립트는 엔드포인트가 갖춰진 뒤 활성화한다.
 * 현재는 placeholder로 /api/v1/tenants/me, /api/v1/members 등 기존 엔드포인트를 호출해
 * 대시보드 초기 페이로드 부하를 시뮬레이션한다.
 */
import http from 'k6/http';
import { check, sleep } from 'k6';

import {
  BASE_URL,
  COMMON_THRESHOLDS,
  authHeaders,
  obtainToken,
  handleSummary,
} from './lib/config.js';

export const options = {
  scenarios: {
    dashboard_load: {
      executor: 'constant-arrival-rate',
      rate: 30,
      timeUnit: '1s',
      duration: '1m',
      preAllocatedVUs: 20,
      maxVUs: 80,
    },
  },
  thresholds: {
    ...COMMON_THRESHOLDS,
    http_req_duration: ['p(99)<400', 'p(95)<280'],
  },
};

export function setup() {
  return { token: obtainToken() };
}

export default function (data) {
  const headers = authHeaders(data.token);
  const reqs = http.batch([
    ['GET', `${BASE_URL}/api/v1/tenants/me`, null, { headers, tags: { name: 'tenant_me' } }],
    ['GET', `${BASE_URL}/api/v1/libraries?size=20`, null, { headers, tags: { name: 'libraries' } }],
    ['GET', `${BASE_URL}/api/v1/members?status=ACTIVE&size=10`, null, { headers, tags: { name: 'members_recent' } }],
    ['GET', `${BASE_URL}/api/v1/codes/groups`, null, { headers, tags: { name: 'codes_groups' } }],
  ]);
  reqs.forEach((res, idx) => {
    check(res, { [`status 200 (#${idx})`]: (r) => r.status === 200 });
  });
  sleep(0.5);
}

export { handleSummary };
