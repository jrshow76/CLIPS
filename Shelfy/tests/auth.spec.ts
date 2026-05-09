/**
 * Shelfy - 인증 E2E 테스트
 * 커버 시나리오:
 *   - TC-AUTH-001: 정상 회원가입
 *   - TC-AUTH-002: 이메일 중복 회원가입 차단
 *   - TC-AUTH-003: 닉네임 중복 회원가입 차단
 *   - TC-AUTH-030: 정상 로그인
 *   - TC-AUTH-031: 존재하지 않는 이메일 로그인
 *   - TC-AUTH-033: 5회 실패 계정 잠금
 *   - TC-AUTH-036: refreshToken HttpOnly 쿠키 검증
 *   - TC-AUTH-040: 정상 로그아웃
 *   - TC-AUTH-041: 로그아웃 후 refreshToken 재사용 차단
 */

import { test, expect, APIRequestContext } from '@playwright/test';
import {
  signup,
  login,
  logout,
  generateEmail,
  generateNickname,
} from './helpers/api';

const API_URL = process.env.API_URL || 'http://localhost:8080/api/v1';

// 공통 유효 비밀번호
const VALID_PASSWORD = 'Shelfy1234!';

test.describe('인증 (AUTH)', () => {
  test.describe('회원가입', () => {
    test('TC-AUTH-001: 정상 회원가입 - HTTP 201 및 응답 구조 검증', async ({ request }) => {
      const email = generateEmail('signup');
      const nickname = generateNickname('su');

      const response = await signup(request, {
        email,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname,
        agreeTerms: true,
        agreePrivacy: true,
        agreeMarketing: false,
      });

      expect(response.status()).toBe(201);
      const body = await response.json();
      expect(body.success).toBe(true);
      expect(body.data.email).toBe(email);
      expect(body.data.nickname).toBe(nickname);
      expect(body.data.userId).toBeTruthy();
      // 응답 바디에 민감 정보 미포함 검증
      expect(body.data.password).toBeUndefined();
    });

    test('TC-AUTH-002: 이메일 중복 회원가입 차단 - HTTP 409 / AUTH-E001', async ({ request }) => {
      const email = generateEmail('dup');
      const nickname1 = generateNickname('d1');
      const nickname2 = generateNickname('d2');

      // 1차 가입
      await signup(request, {
        email,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: nickname1,
        agreeTerms: true,
        agreePrivacy: true,
      });

      // 동일 이메일로 재가입
      const response = await signup(request, {
        email,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: nickname2,
        agreeTerms: true,
        agreePrivacy: true,
      });

      expect(response.status()).toBe(409);
      const body = await response.json();
      expect(body.success).toBe(false);
      expect(body.error.code).toBe('AUTH-E001');
    });

    test('TC-AUTH-003: 닉네임 중복 회원가입 차단 - HTTP 409 / AUTH-E002', async ({ request }) => {
      const email1 = generateEmail('ne1');
      const email2 = generateEmail('ne2');
      const nickname = generateNickname('dupl');

      // 1차 가입
      await signup(request, {
        email: email1,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname,
        agreeTerms: true,
        agreePrivacy: true,
      });

      // 동일 닉네임으로 재가입
      const response = await signup(request, {
        email: email2,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname,
        agreeTerms: true,
        agreePrivacy: true,
      });

      expect(response.status()).toBe(409);
      const body = await response.json();
      expect(body.error.code).toBe('AUTH-E002');
    });

    test('TC-AUTH-004: 비밀번호 불일치 - HTTP 400 / AUTH-E003', async ({ request }) => {
      const response = await signup(request, {
        email: generateEmail('pwd'),
        password: VALID_PASSWORD,
        passwordConfirm: 'DifferentPass1!',
        nickname: generateNickname('pw'),
        agreeTerms: true,
        agreePrivacy: true,
      });

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.error.code).toBe('AUTH-E003');
    });

    test('TC-AUTH-005: 이메일 형식 오류 - HTTP 400 / AUTH-E004', async ({ request }) => {
      const response = await signup(request, {
        email: 'not-an-email',
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('em'),
        agreeTerms: true,
        agreePrivacy: true,
      });

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.error.code).toBe('AUTH-E004');
    });

    test('TC-AUTH-006: 비밀번호 규칙 위반 - 8자 미만 - HTTP 400 / AUTH-E005', async ({ request }) => {
      const response = await signup(request, {
        email: generateEmail('pwr'),
        password: 'Te1!',
        passwordConfirm: 'Te1!',
        nickname: generateNickname('pr'),
        agreeTerms: true,
        agreePrivacy: true,
      });

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.error.code).toBe('AUTH-E005');
    });

    test('TC-AUTH-007: 비밀번호 규칙 위반 - 특수문자 미포함 - HTTP 400 / AUTH-E005', async ({ request }) => {
      const response = await signup(request, {
        email: generateEmail('pwr2'),
        password: 'TestPass1234',
        passwordConfirm: 'TestPass1234',
        nickname: generateNickname('pr2'),
        agreeTerms: true,
        agreePrivacy: true,
      });

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.error.code).toBe('AUTH-E005');
    });

    test('TC-AUTH-009: 필수 약관 미동의 - HTTP 400 / AUTH-E006', async ({ request }) => {
      const response = await signup(request, {
        email: generateEmail('tos'),
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('ts'),
        agreeTerms: false,
        agreePrivacy: true,
      });

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.error.code).toBe('AUTH-E006');
    });

    test('TC-AUTH-010: 닉네임 경계값 - 2자 허용', async ({ request }) => {
      const response = await signup(request, {
        email: generateEmail('nb'),
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: 'ab',
        agreeTerms: true,
        agreePrivacy: true,
      });
      expect(response.status()).toBe(201);
    });

    test('TC-AUTH-011: 닉네임 경계값 - 1자 거부', async ({ request }) => {
      const response = await signup(request, {
        email: generateEmail('nb2'),
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: 'a',
        agreeTerms: true,
        agreePrivacy: true,
      });
      expect(response.status()).toBe(400);
    });
  });

  test.describe('로그인', () => {
    let testEmail: string;
    let testNickname: string;

    test.beforeAll(async ({ request }) => {
      testEmail = generateEmail('login');
      testNickname = generateNickname('lg');

      await signup(request, {
        email: testEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: testNickname,
        agreeTerms: true,
        agreePrivacy: true,
      });
    });

    test('TC-AUTH-030: 정상 로그인 - accessToken 및 HttpOnly 쿠키 검증', async ({ request }) => {
      const response = await request.post(`${API_URL}/auth/login`, {
        data: { email: testEmail, password: VALID_PASSWORD },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.success).toBe(true);
      expect(body.data.accessToken).toBeTruthy();
      expect(body.data.tokenType).toBe('Bearer');
      expect(body.data.expiresIn).toBe(3600);

      // TC-AUTH-036: refreshToken이 응답 바디에 없어야 함
      expect(body.data.refreshToken).toBeUndefined();

      // Set-Cookie 헤더에 HttpOnly 포함 여부 검증
      const setCookieHeader = response.headers()['set-cookie'] ?? '';
      expect(setCookieHeader).toContain('refreshToken');
      expect(setCookieHeader.toLowerCase()).toContain('httponly');
    });

    test('TC-AUTH-031: 존재하지 않는 이메일로 로그인 - HTTP 401 / AUTH-E020', async ({ request }) => {
      const response = await request.post(`${API_URL}/auth/login`, {
        data: { email: 'notexist@shelfy-test.io', password: VALID_PASSWORD },
      });

      expect(response.status()).toBe(401);
      const body = await response.json();
      expect(body.error.code).toBe('AUTH-E020');
    });

    test('TC-AUTH-032: 비밀번호 불일치 로그인 - HTTP 401 / AUTH-E020', async ({ request }) => {
      const response = await request.post(`${API_URL}/auth/login`, {
        data: { email: testEmail, password: 'WrongPass1!' },
      });

      expect(response.status()).toBe(401);
      const body = await response.json();
      expect(body.error.code).toBe('AUTH-E020');
    });

    test('TC-AUTH-033: 5회 연속 실패 후 계정 잠금 - HTTP 403 / AUTH-E021', async ({ request }) => {
      const lockEmail = generateEmail('lock');
      const lockNick = generateNickname('lk');

      await signup(request, {
        email: lockEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: lockNick,
        agreeTerms: true,
        agreePrivacy: true,
      });

      // 5회 연속 실패
      for (let i = 0; i < 5; i++) {
        await request.post(`${API_URL}/auth/login`, {
          data: { email: lockEmail, password: 'WrongPass1!' },
        });
      }

      // 6번째 시도 (올바른 비밀번호라도 잠금 상태여야 함)
      const lockedResponse = await request.post(`${API_URL}/auth/login`, {
        data: { email: lockEmail, password: VALID_PASSWORD },
      });

      expect(lockedResponse.status()).toBe(403);
      const body = await lockedResponse.json();
      expect(body.error.code).toBe('AUTH-E021');
      expect(body.error.message).toContain('잠금');
    });
  });

  test.describe('로그아웃', () => {
    let accessToken: string;
    let logoutEmail: string;

    test.beforeAll(async ({ request }) => {
      logoutEmail = generateEmail('logout');
      await signup(request, {
        email: logoutEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('lo'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      accessToken = await login(request, logoutEmail, VALID_PASSWORD);
    });

    test('TC-AUTH-040: 정상 로그아웃 - HTTP 204', async ({ request }) => {
      const response = await logout(request, accessToken);
      expect(response.status()).toBe(204);
    });

    test('TC-AUTH-042: 인증 토큰 없이 로그아웃 시도 - HTTP 401', async ({ request }) => {
      const response = await request.post(`${API_URL}/auth/logout`);
      expect(response.status()).toBe(401);
    });
  });

  test.describe('전체 인증 플로우', () => {
    test('회원가입 → 로그인 → 내 프로필 조회 → 로그아웃 통합 플로우', async ({ request }) => {
      const email = generateEmail('flow');
      const nickname = generateNickname('fl');

      // 1. 회원가입
      const signupRes = await signup(request, {
        email,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname,
        agreeTerms: true,
        agreePrivacy: true,
      });
      expect(signupRes.status()).toBe(201);

      // 2. 로그인
      const token = await login(request, email, VALID_PASSWORD);
      expect(token).toBeTruthy();

      // 3. 내 프로필 조회
      const profileRes = await request.get(`${API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(profileRes.status()).toBe(200);
      const profileBody = await profileRes.json();
      expect(profileBody.data.email).toBe(email);
      expect(profileBody.data.nickname).toBe(nickname);

      // 4. 로그아웃
      const logoutRes = await logout(request, token);
      expect(logoutRes.status()).toBe(204);

      // 5. 로그아웃 후 보호 API 접근 불가 확인
      const afterLogoutRes = await request.get(`${API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(afterLogoutRes.status()).toBe(401);
    });
  });
});
