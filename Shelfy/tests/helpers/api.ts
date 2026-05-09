import { APIRequestContext } from '@playwright/test';

const API_URL = process.env.API_URL || 'http://localhost:8080/api/v1';

export interface SignupPayload {
  email: string;
  password: string;
  passwordConfirm: string;
  nickname: string;
  agreeTerms: boolean;
  agreePrivacy: boolean;
  agreeMarketing?: boolean;
}

export interface LoginResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
}

/**
 * 회원가입 API 호출
 */
export async function signup(
  request: APIRequestContext,
  payload: SignupPayload
) {
  const response = await request.post(`${API_URL}/auth/signup`, {
    data: payload,
  });
  return response;
}

/**
 * 로그인 API 호출 후 accessToken 반환
 */
export async function login(
  request: APIRequestContext,
  email: string,
  password: string
): Promise<string> {
  const response = await request.post(`${API_URL}/auth/login`, {
    data: { email, password },
  });
  if (!response.ok()) {
    throw new Error(`로그인 실패: ${response.status()} ${await response.text()}`);
  }
  const body = await response.json();
  return body.data.accessToken;
}

/**
 * 로그아웃 API 호출
 */
export async function logout(
  request: APIRequestContext,
  accessToken: string
) {
  return request.post(`${API_URL}/auth/logout`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

/**
 * 상품 등록 API 호출
 */
export async function createItem(
  request: APIRequestContext,
  accessToken: string,
  payload: Record<string, unknown>
) {
  return request.post(`${API_URL}/items`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    data: payload,
  });
}

/**
 * 구매 주문 API 호출
 */
export async function createOrder(
  request: APIRequestContext,
  accessToken: string,
  itemId: number,
  paymentMethod = 'CARD'
) {
  return request.post(`${API_URL}/orders`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    data: { itemId, paymentMethod },
  });
}

/**
 * 구독 신청 API 호출
 */
export async function createSubscription(
  request: APIRequestContext,
  accessToken: string,
  itemId: number,
  planId: number,
  paymentMethod = 'CARD'
) {
  return request.post(`${API_URL}/subscriptions`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    data: { itemId, planId, paymentMethod },
  });
}

/**
 * 테스트용 고유 이메일 생성
 */
export function generateEmail(prefix = 'test'): string {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 10000)}@shelfy-test.io`;
}

/**
 * 테스트용 고유 닉네임 생성
 */
export function generateNickname(prefix = 'nick'): string {
  return `${prefix}_${Date.now().toString().slice(-6)}`;
}
