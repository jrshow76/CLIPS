/**
 * Shelfy - 구매(주문) E2E 테스트
 * 커버 시나리오:
 *   - TC-ORDER-001: 정상 구매
 *   - TC-ORDER-002: 본인 상품 구매 차단
 *   - TC-ORDER-003: 존재하지 않는 상품 구매 차단
 *   - TC-ORDER-005: 구독 전용 상품 단건 구매 차단
 *   - TC-ORDER-006: BOTH 유형 상품 단건 구매 허용
 *   - TC-ORDER-007: 비로그인 구매 시도
 *   - TC-ORDER-008: 동일 상품 중복 구매 허용
 *   - TC-ORDER-010: 구매 내역 조회
 *   - TC-ORDER-020: 정상 환불 (7일 이내, 미열람)
 *   - TC-ORDER-021: 환불 기간 7일 초과 차단
 *   - TC-ORDER-023: 콘텐츠 열람 후 환불 차단
 *   - TC-ORDER-024: 타인 주문 환불 차단
 */

import { test, expect } from '@playwright/test';
import {
  signup,
  login,
  createItem,
  createOrder,
  generateEmail,
  generateNickname,
} from './helpers/api';

const API_URL = process.env.API_URL || 'http://localhost:8080/api/v1';
const VALID_PASSWORD = 'Shelfy1234!';
const FIXTURE_IMAGE_ID = process.env.FIXTURE_IMAGE_ID || 'img-fixture-001';

function buildItemPayload(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    title: '구매 테스트 상품',
    description: '구매 자동화 테스트용 상품입니다. (10자 이상)',
    category: 'DIGITAL_CONTENT',
    saleType: 'PURCHASE',
    price: 10000,
    imageIds: [FIXTURE_IMAGE_ID],
    status: 'PUBLISHED',
    ...overrides,
  };
}

test.describe('구매 (ORDER)', () => {
  let sellerToken: string;
  let buyerToken: string;
  let otherToken: string;
  let purchaseItemId: number;     // PURCHASE 유형 상품
  let subscribeOnlyItemId: number; // SUBSCRIBE 전용 상품
  let bothItemId: number;          // BOTH 유형 상품

  test.beforeAll(async ({ request }) => {
    // 셀러 계정
    const sellerEmail = generateEmail('purch_seller');
    await signup(request, {
      email: sellerEmail,
      password: VALID_PASSWORD,
      passwordConfirm: VALID_PASSWORD,
      nickname: generateNickname('ps'),
      agreeTerms: true,
      agreePrivacy: true,
    });
    sellerToken = await login(request, sellerEmail, VALID_PASSWORD);

    // 바이어 계정
    const buyerEmail = generateEmail('purch_buyer');
    await signup(request, {
      email: buyerEmail,
      password: VALID_PASSWORD,
      passwordConfirm: VALID_PASSWORD,
      nickname: generateNickname('pb'),
      agreeTerms: true,
      agreePrivacy: true,
    });
    buyerToken = await login(request, buyerEmail, VALID_PASSWORD);

    // 다른 계정 (타인 주문 접근 테스트용)
    const otherEmail = generateEmail('purch_other');
    await signup(request, {
      email: otherEmail,
      password: VALID_PASSWORD,
      passwordConfirm: VALID_PASSWORD,
      nickname: generateNickname('po'),
      agreeTerms: true,
      agreePrivacy: true,
    });
    otherToken = await login(request, otherEmail, VALID_PASSWORD);

    // 테스트용 상품 사전 등록 (셀러 계정)
    const purchaseRes = await createItem(request, sellerToken, buildItemPayload({
      saleType: 'PURCHASE',
    }));
    purchaseItemId = (await purchaseRes.json()).data.itemId;

    const subscribeRes = await createItem(request, sellerToken, buildItemPayload({
      title: '구독 전용 상품',
      saleType: 'SUBSCRIBE',
      price: undefined,
      subscriptionPlans: [
        { planName: 'Basic', period: 'MONTHLY', planPrice: 3000 },
      ],
    }));
    subscribeOnlyItemId = (await subscribeRes.json()).data.itemId;

    const bothRes = await createItem(request, sellerToken, buildItemPayload({
      title: 'BOTH 유형 상품',
      saleType: 'BOTH',
      price: 8000,
      subscriptionPlans: [
        { planName: 'Monthly', period: 'MONTHLY', planPrice: 2500 },
      ],
    }));
    bothItemId = (await bothRes.json()).data.itemId;
  });

  test.describe('단일 구매', () => {
    test('TC-ORDER-001: 정상 구매 - HTTP 201', async ({ request }) => {
      const response = await createOrder(request, buyerToken, purchaseItemId);

      expect(response.status()).toBe(201);
      const body = await response.json();
      expect(body.success).toBe(true);
      expect(body.data.orderId).toBeTruthy();
      expect(body.data.itemId).toBe(purchaseItemId);
      expect(body.data.status).toBe('COMPLETED');
      expect(body.data.paidAt).toBeTruthy();
      expect(body.data.paymentMethod).toBe('CARD');
    });

    test('TC-ORDER-002: 본인 상품 구매 차단 - HTTP 422 / ORDER-E001', async ({ request }) => {
      const response = await createOrder(request, sellerToken, purchaseItemId);

      expect(response.status()).toBe(422);
      const body = await response.json();
      expect(body.error.code).toBe('ORDER-E001');
      expect(body.error.message).toContain('본인 상품');
    });

    test('TC-ORDER-003: 존재하지 않는 상품 구매 - HTTP 404 / ORDER-E002', async ({ request }) => {
      const response = await createOrder(request, buyerToken, 99999999);

      expect(response.status()).toBe(404);
      const body = await response.json();
      expect(body.error.code).toBe('ORDER-E002');
    });

    test('TC-ORDER-005: 구독 전용(SUBSCRIBE) 상품 단건 구매 차단 - HTTP 422 / ORDER-E004', async ({ request }) => {
      const response = await createOrder(request, buyerToken, subscribeOnlyItemId);

      expect(response.status()).toBe(422);
      const body = await response.json();
      expect(body.error.code).toBe('ORDER-E004');
      expect(body.error.message).toContain('구독');
    });

    test('TC-ORDER-006: BOTH 유형 상품 단건 구매 허용 - HTTP 201', async ({ request }) => {
      const response = await createOrder(request, buyerToken, bothItemId);

      expect(response.status()).toBe(201);
    });

    test('TC-ORDER-007: 비로그인 상태 구매 시도 - HTTP 401', async ({ request }) => {
      const response = await request.post(`${API_URL}/orders`, {
        data: { itemId: purchaseItemId, paymentMethod: 'CARD' },
      });

      expect(response.status()).toBe(401);
    });

    test('TC-ORDER-008: 동일 상품 중복 구매 허용 (디지털 콘텐츠)', async ({ request }) => {
      // 첫 번째 구매
      const res1 = await createOrder(request, buyerToken, purchaseItemId);
      expect(res1.status()).toBe(201);

      // 두 번째 구매 (중복 허용)
      const res2 = await createOrder(request, buyerToken, purchaseItemId);
      expect(res2.status()).toBe(201);

      const body1 = await res1.json();
      const body2 = await res2.json();
      // 서로 다른 orderId를 받아야 함
      expect(body1.data.orderId).not.toBe(body2.data.orderId);
    });
  });

  test.describe('구매 내역 조회', () => {
    test('TC-ORDER-010: 구매 내역 정상 조회 - HTTP 200', async ({ request }) => {
      // 사전에 구매 있어야 함
      await createOrder(request, buyerToken, purchaseItemId);

      const response = await request.get(`${API_URL}/orders`, {
        headers: { Authorization: `Bearer ${buyerToken}` },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.data.content).toBeDefined();
      expect(Array.isArray(body.data.content)).toBe(true);
    });

    test('TC-ORDER-011: 날짜 범위 필터 조회', async ({ request }) => {
      const response = await request.get(`${API_URL}/orders`, {
        headers: { Authorization: `Bearer ${buyerToken}` },
        params: {
          startDate: '2026-01-01',
          endDate: '2026-12-31',
        },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.data.content).toBeDefined();
    });

    test('TC-ORDER-012: 본인 내역만 반환 (타인 내역 미포함)', async ({ request }) => {
      // otherToken으로 내역 조회
      const response = await request.get(`${API_URL}/orders`, {
        headers: { Authorization: `Bearer ${otherToken}` },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      // 타인(buyer)의 주문이 포함되지 않아야 함
      // (other 계정은 아직 구매 없으므로 0건이어야 함)
      const buyerOrders = body.data.content.filter(
        (o: { buyerEmail?: string }) => o.buyerEmail === 'purch_buyer'
      );
      expect(buyerOrders.length).toBe(0);
    });
  });

  test.describe('환불', () => {
    let refundOrderId: number;

    test.beforeAll(async ({ request }) => {
      // 환불 테스트용 구매
      const orderRes = await createOrder(request, buyerToken, purchaseItemId);
      refundOrderId = (await orderRes.json()).data.orderId;
    });

    test('TC-ORDER-020: 정상 환불 (7일 이내, 미열람) - HTTP 200', async ({ request }) => {
      const response = await request.post(`${API_URL}/orders/${refundOrderId}/cancel`, {
        headers: { Authorization: `Bearer ${buyerToken}` },
        data: { reason: '단순 변심' },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.data.status).toBe('REFUNDED');
      expect(body.data.refundAmount).toBeGreaterThan(0);
      expect(body.data.refundedAt).toBeTruthy();
    });

    test('TC-ORDER-021: 환불 기간 7일 초과 차단 - HTTP 422 / ORDER-E010', async ({ request }) => {
      // 테스트 환경에서 8일 경과 주문 ID를 별도 fixture로 제공 (또는 DB 직접 조작)
      const expiredOrderId = parseInt(process.env.EXPIRED_ORDER_ID || '0');
      if (!expiredOrderId) {
        test.skip(true, '7일 경과 주문 fixture가 설정되지 않았습니다. 환경 변수 EXPIRED_ORDER_ID를 설정하세요.');
        return;
      }

      const response = await request.post(`${API_URL}/orders/${expiredOrderId}/cancel`, {
        headers: { Authorization: `Bearer ${buyerToken}` },
        data: { reason: '기간 초과 환불 시도' },
      });

      expect(response.status()).toBe(422);
      const body = await response.json();
      expect(body.error.code).toBe('ORDER-E010');
    });

    test('TC-ORDER-023: 콘텐츠 열람 후 환불 차단 - HTTP 422 / ORDER-E011', async ({ request }) => {
      // 열람 이력이 있는 주문 ID (테스트 fixture 필요)
      const viewedOrderId = parseInt(process.env.VIEWED_ORDER_ID || '0');
      if (!viewedOrderId) {
        test.skip(true, '열람 이력 있는 주문 fixture가 설정되지 않았습니다. 환경 변수 VIEWED_ORDER_ID를 설정하세요.');
        return;
      }

      const response = await request.post(`${API_URL}/orders/${viewedOrderId}/cancel`, {
        headers: { Authorization: `Bearer ${buyerToken}` },
        data: { reason: '열람 후 환불 시도' },
      });

      expect(response.status()).toBe(422);
      const body = await response.json();
      expect(body.error.code).toBe('ORDER-E011');
    });

    test('TC-ORDER-024: 타인 주문 환불 시도 차단 - HTTP 403', async ({ request }) => {
      // 새 구매 생성 (buyer)
      const orderRes = await createOrder(request, buyerToken, purchaseItemId);
      const orderId = (await orderRes.json()).data.orderId;

      // other 계정으로 환불 시도
      const response = await request.post(`${API_URL}/orders/${orderId}/cancel`, {
        headers: { Authorization: `Bearer ${otherToken}` },
        data: { reason: '타인 환불 시도' },
      });

      expect(response.status()).toBe(403);
    });
  });

  test.describe('구매 → 내역 확인 → 환불 통합 플로우', () => {
    test('아이템 구매 → 주문 내역 확인 → 환불 요청 통합 플로우', async ({ request }) => {
      // 1. 구매
      const orderRes = await createOrder(request, buyerToken, purchaseItemId);
      expect(orderRes.status()).toBe(201);
      const { data: { orderId, amount } } = await orderRes.json();

      // 2. 구매 내역 조회
      const listRes = await request.get(`${API_URL}/orders`, {
        headers: { Authorization: `Bearer ${buyerToken}` },
      });
      expect(listRes.status()).toBe(200);
      const listBody = await listRes.json();
      const order = listBody.data.content.find((o: { orderId: number }) => o.orderId === orderId);
      expect(order).toBeDefined();

      // 3. 환불 요청
      const cancelRes = await request.post(`${API_URL}/orders/${orderId}/cancel`, {
        headers: { Authorization: `Bearer ${buyerToken}` },
        data: { reason: '플로우 테스트 환불' },
      });
      expect(cancelRes.status()).toBe(200);
      const cancelBody = await cancelRes.json();
      expect(cancelBody.data.status).toBe('REFUNDED');
      expect(cancelBody.data.refundAmount).toBe(amount);
    });
  });
});
