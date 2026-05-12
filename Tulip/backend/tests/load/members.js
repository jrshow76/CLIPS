/**
 * k6 부하 — 회원 목록 검색
 * Phase 1-D 목표: 50 RPS, P99 < 300ms
 *
 * 실행: k6 run members.js
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
    members_search: {
      executor: 'constant-arrival-rate',
      rate: 50,
      timeUnit: '1s',
      duration: '1m',
      preAllocatedVUs: 30,
      maxVUs: 120,
    },
  },
  thresholds: {
    ...COMMON_THRESHOLDS,
    http_req_duration: ['p(99)<300', 'p(95)<200'],
  },
};

export function setup() {
  return { token: obtainToken() };
}

const KEYWORDS = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임'];

export default function (data) {
  const q = KEYWORDS[Math.floor(Math.random() * KEYWORDS.length)];
  const url = `${BASE_URL}/api/v1/members?q=${encodeURIComponent(q)}&page=0&size=20`;
  const res = http.get(url, {
    headers: authHeaders(data.token),
    tags: { name: 'members_search' },
  });
  check(res, {
    'status 200': (r) => r.status === 200,
    'has items': (r) => {
      const body = r.json();
      return body && body.data && Array.isArray(body.data.items);
    },
  });
  sleep(0.2);
}

export { handleSummary };
