/**
 * k6 공용 설정 — Tulip+ 부하 테스트 (Phase 1-D)
 * ---------------------------------------------------------------
 * - baseURL, 토큰 헬퍼, 공통 thresholds, summary export
 *
 * 환경변수:
 *   BASE_URL          : API 게이트웨이 베이스 (기본: http://localhost:8080)
 *   IAM_BASE_URL      : iam-service 베이스 (기본: BASE_URL과 동일)
 *   TEST_USERNAME     : Direct Grant 사용자 (기본: librarian@demo-tenant-1)
 *   TEST_PASSWORD     : 비밀번호 (기본: changeit)
 *   TEST_TENANT_ID    : 테넌트 ID (기본: demo-tenant-1)
 *   K6_KEYCLOAK_REALM : Keycloak realm (기본: tulip)
 *   K6_KEYCLOAK_CLIENT: Client ID (기본: tulip-admin)
 */
import http from 'k6/http';
import { check } from 'k6';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js';

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
export const IAM_BASE_URL = __ENV.IAM_BASE_URL || BASE_URL;
export const TEST_USERNAME = __ENV.TEST_USERNAME || 'librarian@demo-tenant-1';
export const TEST_PASSWORD = __ENV.TEST_PASSWORD || 'changeit';
export const TEST_TENANT_ID = __ENV.TEST_TENANT_ID || 'demo-tenant-1';
export const KC_REALM = __ENV.K6_KEYCLOAK_REALM || 'tulip';
export const KC_CLIENT = __ENV.K6_KEYCLOAK_CLIENT || 'tulip-admin';

/** 공통 thresholds — 각 스크립트가 추가 항목을 확장 가능. */
export const COMMON_THRESHOLDS = {
  http_req_failed: ['rate<0.01'], // 1% 미만 실패율
  checks: ['rate>0.99'],
};

/**
 * Direct Grant (Resource Owner Password Credentials) 로 액세스 토큰 발급.
 * 운영에서는 사용 금지 — 부하 테스트 전용.
 */
export function obtainToken() {
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
    tags: { name: 'kc_token' },
  });
  check(res, {
    'token 200': (r) => r.status === 200,
    'token has access_token': (r) => !!(r.json() && r.json().access_token),
  });
  return (res.json() && res.json().access_token) || '';
}

/** 표준 인증 헤더 + 트레이스 헤더. */
export function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    'X-Tenant-Id': TEST_TENANT_ID,
    'Content-Type': 'application/json',
  };
}

/** 모든 스크립트가 사용할 HTML 리포트 생성기. */
export function handleSummary(data) {
  return {
    'summary.html': htmlReport(data),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}
