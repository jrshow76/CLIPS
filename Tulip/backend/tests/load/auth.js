/**
 * k6 부하 — 로그인 API
 * Phase 1-B DoD: 100 RPS, P99 < 200ms
 *
 * 실행: k6 run auth.js
 */
import http from 'k6/http';
import { check, sleep } from 'k6';

import {
  IAM_BASE_URL,
  KC_REALM,
  KC_CLIENT,
  TEST_USERNAME,
  TEST_PASSWORD,
  COMMON_THRESHOLDS,
  handleSummary,
} from './lib/config.js';

export const options = {
  scenarios: {
    login: {
      executor: 'constant-arrival-rate',
      rate: 100,
      timeUnit: '1s',
      duration: '1m',
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
  thresholds: {
    ...COMMON_THRESHOLDS,
    http_req_duration: ['p(99)<200', 'p(95)<150'],
  },
};

export default function () {
  const url = `${IAM_BASE_URL}/realms/${KC_REALM}/protocol/openid-connect/token`;
  const payload = {
    grant_type: 'password',
    client_id: KC_CLIENT,
    username: TEST_USERNAME,
    password: TEST_PASSWORD,
    scope: 'openid profile email',
  };
  const res = http.post(url, payload, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    tags: { name: 'login' },
  });
  check(res, {
    'status 200': (r) => r.status === 200,
    'has access_token': (r) => !!(r.json() && r.json().access_token),
  });
  sleep(0.1);
}

export { handleSummary };
