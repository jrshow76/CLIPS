/**
 * Shelfy - 구독 E2E 테스트
 * 커버 시나리오:
 *   - TC-SUB-001: 정상 구독 신청
 *   - TC-SUB-002: 본인 상품 구독 차단
 *   - TC-SUB-003: 중복 구독 방지
 *   - TC-SUB-004: Race Condition 중복 구독 방지
 *   - TC-SUB-005: PURCHASE 전용 상품 구독 차단
 *   - TC-SUB-006~008: 다음 결제일 계산 검증
 *   - TC-SUB-010: 정상 구독 해지 신청
 *   - TC-SUB-011: 해지 후 기간 내 서비스 이용 가능
 *   - TC-SUB-013: 타인 구독 해지 차단
 *   - TC-SUB-020: 구독 해지 취소 (재활성화)
 *   - TC-SUB-030~031: 구독 내역 조회
 */

import { test, expect } from '@playwright/test';
import {
  signup,
  login,
  createItem,
  createSubscription,
  generateEmail,
  generateNickname,
} from './helpers/api';

const API_URL = process.env.API_URL || 'http://localhost:8080/api/v1';
const VALID_PASSWORD = 'Shelfy1234!';
const FIXTURE_IMAGE_ID = process.env.FIXTURE_IMAGE_ID || 'img-fixture-001';

function buildSubscribeItemPayload(period: 'MONTHLY' | 'QUARTERLY' | 'YEARLY' = 'MONTHLY'): Record<string, unknown> {
  return {
    title: `구독 테스트 상품 (${period})`,
    description: '구독 자동화 테스트용 상품입니다. (10자 이상)',
    category: 'COURSE',
    saleType: 'SUBSCRIBE',
    imageIds: [FIXTURE_IMAGE_ID],
    status: 'PUBLISHED',
    subscriptionPlans: [
      {
        planName: 'Basic',
        period,
        planPrice: period === 'MONTHLY' ? 5000 : period === 'QUARTERLY' ? 12000 : 40000,
        description: `${period} 플랜`,
      },
    ],
  };
}

/**
 * Date 비교 헬퍼: 두 날짜의 차이가 expectedMonths ± 1일 이내인지 확인
 */
function isApproximatelyMonthsLater(start: string, end: string, months: number): boolean {
  const startDate = new Date(start);
  const endDate = new Date(end);
  const expectedDate = new Date(start);
  expectedDate.setMonth(expectedDate.getMonth() + months);

  const diffMs = Math.abs(endDate.getTime() - expectedDate.getTime());
  const oneDayMs = 24 * 60 * 60 * 1000;
  return diffMs <= oneDayMs;
}

test.describe('구독 (SUB)', () => {
  let sellerToken: string;
  let subscriberToken: string;
  let otherToken: string;

  // 구독 가능 상품 (MONTHLY)
  let monthlyItemId: number;
  let monthlyPlanId: number;

  // QUARTERLY 상품
  let quarterlyItemId: number;
  let quarterlyPlanId: number;

  // YEARLY 상품
  let yearlyItemId: number;
  let yearlyPlanId: number;

  // PURCHASE 전용 상품 (구독 불가)
  let purchaseOnlyItemId: number;

  test.beforeAll(async ({ request }) => {
    // 셀러 계정
    const sellerEmail = generateEmail('sub_seller');
    await signup(request, {
      email: sellerEmail,
      password: VALID_PASSWORD,
      passwordConfirm: VALID_PASSWORD,
      nickname: generateNickname('ss'),
      agreeTerms: true,
      agreePrivacy: true,
    });
    sellerToken = await login(request, sellerEmail, VALID_PASSWORD);

    // 구독자 계정
    const subEmail = generateEmail('subscriber');
    await signup(request, {
      email: subEmail,
      password: VALID_PASSWORD,
      passwordConfirm: VALID_PASSWORD,
      nickname: generateNickname('sb'),
      agreeTerms: true,
      agreePrivacy: true,
    });
    subscriberToken = await login(request, subEmail, VALID_PASSWORD);

    // 타인 계정
    const otherEmail = generateEmail('sub_other');
    await signup(request, {
      email: otherEmail,
      password: VALID_PASSWORD,
      passwordConfirm: VALID_PASSWORD,
      nickname: generateNickname('so'),
      agreeTerms: true,
      agreePrivacy: true,
    });
    otherToken = await login(request, otherEmail, VALID_PASSWORD);

    // MONTHLY 상품 등록
    const monthlyRes = await createItem(request, sellerToken, buildSubscribeItemPayload('MONTHLY'));
    const monthlyBody = await monthlyRes.json();
    monthlyItemId = monthlyBody.data.itemId;

    // planId 획득 (상품 상세 조회)
    const monthlyDetail = await request.get(`${API_URL}/items/${monthlyItemId}`);
    const monthlyDetailBody = await monthlyDetail.json();
    monthlyPlanId = monthlyDetailBody.data.subscriptionPlans[0].planId;

    // QUARTERLY 상품
    const quarterlyRes = await createItem(request, sellerToken, buildSubscribeItemPayload('QUARTERLY'));
    quarterlyItemId = (await quarterlyRes.json()).data.itemId;
    const qDetail = await request.get(`${API_URL}/items/${quarterlyItemId}`);
    quarterlyPlanId = (await qDetail.json()).data.subscriptionPlans[0].planId;

    // YEARLY 상품
    const yearlyRes = await createItem(request, sellerToken, buildSubscribeItemPayload('YEARLY'));
    yearlyItemId = (await yearlyRes.json()).data.itemId;
    const yDetail = await request.get(`${API_URL}/items/${yearlyItemId}`);
    yearlyPlanId = (await yDetail.json()).data.subscriptionPlans[0].planId;

    // PURCHASE 전용 상품
    const purchaseRes = await createItem(request, sellerToken, {
      title: 'PURCHASE 전용 상품',
      description: '구독 불가 테스트용 상품입니다. (10자 이상)',
      category: 'TEMPLATE',
      saleType: 'PURCHASE',
      price: 5000,
      imageIds: [FIXTURE_IMAGE_ID],
      status: 'PUBLISHED',
    });
    purchaseOnlyItemId = (await purchaseRes.json()).data.itemId;
  });

  test.describe('구독 신청', () => {
    test('TC-SUB-001: 정상 구독 신청 (MONTHLY) - HTTP 201', async ({ request }) => {
      const response = await createSubscription(
        request, subscriberToken, monthlyItemId, monthlyPlanId
      );

      expect(response.status()).toBe(201);
      const body = await response.json();
      expect(body.success).toBe(true);
      expect(body.data.subscriptionId).toBeTruthy();
      expect(body.data.status).toBe('ACTIVE');
      expect(body.data.planName).toBe('Basic');
      expect(body.data.nextBillingAt).toBeTruthy();
    });

    test('TC-SUB-002: 본인 상품 구독 차단 - HTTP 422 / SUB-E002', async ({ request }) => {
      const response = await createSubscription(
        request, sellerToken, monthlyItemId, monthlyPlanId
      );

      expect(response.status()).toBe(422);
      const body = await response.json();
      expect(body.error.code).toBe('SUB-E002');
      expect(body.error.message).toContain('본인');
    });

    test('TC-SUB-003: 중복 구독 방지 - HTTP 409 / SUB-E001', async ({ request }) => {
      // 구독 상태가 없는 새 계정으로 테스트
      const dupEmail = generateEmail('dup_sub');
      await signup(request, {
        email: dupEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('ds'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      const dupToken = await login(request, dupEmail, VALID_PASSWORD);

      // 첫 번째 구독
      const first = await createSubscription(request, dupToken, monthlyItemId, monthlyPlanId);
      expect(first.status()).toBe(201);

      // 두 번째 중복 구독 시도
      const second = await createSubscription(request, dupToken, monthlyItemId, monthlyPlanId);
      expect(second.status()).toBe(409);
      const body = await second.json();
      expect(body.error.code).toBe('SUB-E001');
    });

    test('TC-SUB-004: Race Condition - 동시 중복 구독 방지', async ({ request }) => {
      // 새 계정 생성
      const raceEmail = generateEmail('race_sub');
      await signup(request, {
        email: raceEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('rs'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      const raceToken = await login(request, raceEmail, VALID_PASSWORD);

      // 다른 구독 가능한 상품 생성 (race 전용)
      const raceItemRes = await createItem(request, sellerToken, {
        title: 'Race Test 구독 상품',
        description: 'Race Condition 테스트용 구독 상품 (10자 이상)',
        category: 'COURSE',
        saleType: 'SUBSCRIBE',
        imageIds: [FIXTURE_IMAGE_ID],
        status: 'PUBLISHED',
        subscriptionPlans: [
          { planName: 'Race Plan', period: 'MONTHLY', planPrice: 1000 },
        ],
      });
      const raceItemId = (await raceItemRes.json()).data.itemId;
      const raceDetail = await request.get(`${API_URL}/items/${raceItemId}`);
      const racePlanId = (await raceDetail.json()).data.subscriptionPlans[0].planId;

      // 동시 요청 2건 발송
      const [res1, res2] = await Promise.all([
        createSubscription(request, raceToken, raceItemId, racePlanId),
        createSubscription(request, raceToken, raceItemId, racePlanId),
      ]);

      const statuses = [res1.status(), res2.status()];

      // 반드시 한 건만 201, 나머지는 409여야 함
      expect(statuses.filter(s => s === 201).length).toBe(1);
      expect(statuses.filter(s => s === 409).length).toBe(1);

      // 409 응답에 SUB-E001 코드 확인
      const failedRes = res1.status() === 409 ? res1 : res2;
      const failedBody = await failedRes.json();
      expect(failedBody.error.code).toBe('SUB-E001');
    });

    test('TC-SUB-005: PURCHASE 전용 상품 구독 차단 - HTTP 422 / SUB-E003', async ({ request }) => {
      const response = await createSubscription(
        request, subscriberToken, purchaseOnlyItemId, 0
      );

      expect(response.status()).toBe(422);
      const body = await response.json();
      expect(body.error.code).toBe('SUB-E003');
    });

    test('TC-SUB-006: MONTHLY 다음 결제일 계산 정확성 검증', async ({ request }) => {
      const newSubEmail = generateEmail('billing_m');
      await signup(request, {
        email: newSubEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('bm'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      const newToken = await login(request, newSubEmail, VALID_PASSWORD);

      const response = await createSubscription(request, newToken, monthlyItemId, monthlyPlanId);
      expect(response.status()).toBe(201);

      const body = await response.json();
      const { startedAt, nextBillingAt } = body.data;

      // nextBillingAt이 startedAt + 1개월 (±1일 허용)
      expect(isApproximatelyMonthsLater(startedAt, nextBillingAt, 1)).toBe(true);
    });

    test('TC-SUB-007: QUARTERLY 다음 결제일 계산 정확성 검증', async ({ request }) => {
      const qEmail = generateEmail('billing_q');
      await signup(request, {
        email: qEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('bq'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      const qToken = await login(request, qEmail, VALID_PASSWORD);

      const response = await createSubscription(request, qToken, quarterlyItemId, quarterlyPlanId);
      expect(response.status()).toBe(201);

      const body = await response.json();
      expect(isApproximatelyMonthsLater(body.data.startedAt, body.data.nextBillingAt, 3)).toBe(true);
    });

    test('TC-SUB-008: YEARLY 다음 결제일 계산 정확성 검증', async ({ request }) => {
      const yEmail = generateEmail('billing_y');
      await signup(request, {
        email: yEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('by'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      const yToken = await login(request, yEmail, VALID_PASSWORD);

      const response = await createSubscription(request, yToken, yearlyItemId, yearlyPlanId);
      expect(response.status()).toBe(201);

      const body = await response.json();
      expect(isApproximatelyMonthsLater(body.data.startedAt, body.data.nextBillingAt, 12)).toBe(true);
    });
  });

  test.describe('구독 해지', () => {
    let subscriptionId: number;
    let cancelSubToken: string;

    test.beforeAll(async ({ request }) => {
      // 해지 테스트 전용 계정
      const cancelEmail = generateEmail('cancel_sub');
      await signup(request, {
        email: cancelEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('cs'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      cancelSubToken = await login(request, cancelEmail, VALID_PASSWORD);

      // 구독 신청
      const subRes = await createSubscription(request, cancelSubToken, monthlyItemId, monthlyPlanId);
      subscriptionId = (await subRes.json()).data.subscriptionId;
    });

    test('TC-SUB-010: 정상 구독 해지 신청 - HTTP 200, CANCEL_REQUESTED 상태', async ({ request }) => {
      const response = await request.post(
        `${API_URL}/subscriptions/${subscriptionId}/cancel`,
        { headers: { Authorization: `Bearer ${cancelSubToken}` } }
      );

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.data.status).toBe('CANCEL_REQUESTED');
      expect(body.data.cancelledAt).toBeTruthy();
      expect(body.data.activeUntil).toBeTruthy();
    });

    test('TC-SUB-011: 해지 후 CANCEL_REQUESTED 상태에서 activeUntil 노출 확인', async ({ request }) => {
      const response = await request.get(`${API_URL}/subscriptions`, {
        headers: { Authorization: `Bearer ${cancelSubToken}` },
        params: { status: 'CANCEL_REQUESTED' },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      const sub = body.data.content.find(
        (s: { subscriptionId: number }) => s.subscriptionId === subscriptionId
      );
      expect(sub).toBeDefined();
      expect(sub.activeUntil).toBeTruthy();
    });

    test('TC-SUB-013: 타인 구독 해지 시도 차단 - HTTP 403', async ({ request }) => {
      // otherToken으로 cancelSubToken의 구독 해지 시도
      // 다른 구독 ID가 필요하므로 새로 생성
      const subEmail2 = generateEmail('cancel_tgt');
      await signup(request, {
        email: subEmail2,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('ct'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      const subToken2 = await login(request, subEmail2, VALID_PASSWORD);

      const subRes = await createSubscription(request, subToken2, monthlyItemId, monthlyPlanId);
      const targetSubId = (await subRes.json()).data.subscriptionId;

      // otherToken으로 해지 시도
      const response = await request.post(
        `${API_URL}/subscriptions/${targetSubId}/cancel`,
        { headers: { Authorization: `Bearer ${otherToken}` } }
      );

      expect(response.status()).toBe(403);
    });

    test('TC-SUB-014: 이미 해지된 구독 재해지 시도', async ({ request }) => {
      // subscriptionId는 이미 CANCEL_REQUESTED 상태
      const response = await request.post(
        `${API_URL}/subscriptions/${subscriptionId}/cancel`,
        { headers: { Authorization: `Bearer ${cancelSubToken}` } }
      );

      // CANCEL_REQUESTED 또는 이미 해지된 상태 → 409 또는 422
      expect([409, 422]).toContain(response.status());
    });
  });

  test.describe('구독 해지 취소 (재활성화)', () => {
    test('TC-SUB-020: 정상 구독 해지 취소 (재활성화) - HTTP 200, ACTIVE 상태', async ({ request }) => {
      // 전용 계정 생성 및 구독
      const reactEmail = generateEmail('react_sub');
      await signup(request, {
        email: reactEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('ra'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      const reactToken = await login(request, reactEmail, VALID_PASSWORD);

      const subRes = await createSubscription(request, reactToken, monthlyItemId, monthlyPlanId);
      const subId = (await subRes.json()).data.subscriptionId;

      // 해지 신청
      await request.post(
        `${API_URL}/subscriptions/${subId}/cancel`,
        { headers: { Authorization: `Bearer ${reactToken}` } }
      );

      // 재활성화
      const reactivateRes = await request.post(
        `${API_URL}/subscriptions/${subId}/reactivate`,
        { headers: { Authorization: `Bearer ${reactToken}` } }
      );

      expect(reactivateRes.status()).toBe(200);
      const body = await reactivateRes.json();
      expect(body.data.status).toBe('ACTIVE');
    });
  });

  test.describe('구독 내역 조회', () => {
    test('TC-SUB-030: 구독 내역 전체 조회 - HTTP 200', async ({ request }) => {
      const response = await request.get(`${API_URL}/subscriptions`, {
        headers: { Authorization: `Bearer ${subscriberToken}` },
        params: { status: 'ALL' },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.data.content).toBeDefined();
      expect(Array.isArray(body.data.content)).toBe(true);
    });

    test('TC-SUB-031: 활성 구독만 필터 조회 - HTTP 200', async ({ request }) => {
      const response = await request.get(`${API_URL}/subscriptions`, {
        headers: { Authorization: `Bearer ${subscriberToken}` },
        params: { status: 'ACTIVE' },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      const nonActive = body.data.content.filter(
        (s: { status: string }) => s.status !== 'ACTIVE'
      );
      expect(nonActive.length).toBe(0);
    });
  });

  test.describe('구독 신청 → 내역 확인 → 해지 → 재활성화 통합 플로우', () => {
    test('구독 전체 라이프사이클 통합 플로우', async ({ request }) => {
      // 전용 계정
      const flowEmail = generateEmail('sub_flow');
      await signup(request, {
        email: flowEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('sf'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      const flowToken = await login(request, flowEmail, VALID_PASSWORD);

      // 1. 구독 신청
      const subRes = await createSubscription(request, flowToken, monthlyItemId, monthlyPlanId);
      expect(subRes.status()).toBe(201);
      const { data: { subscriptionId: subId, status: activeStatus } } = await subRes.json();
      expect(activeStatus).toBe('ACTIVE');

      // 2. 내역 확인
      const listRes = await request.get(`${API_URL}/subscriptions`, {
        headers: { Authorization: `Bearer ${flowToken}` },
        params: { status: 'ACTIVE' },
      });
      expect(listRes.status()).toBe(200);
      const listBody = await listRes.json();
      const found = listBody.data.content.find(
        (s: { subscriptionId: number }) => s.subscriptionId === subId
      );
      expect(found).toBeDefined();

      // 3. 해지 요청
      const cancelRes = await request.post(
        `${API_URL}/subscriptions/${subId}/cancel`,
        { headers: { Authorization: `Bearer ${flowToken}` } }
      );
      expect(cancelRes.status()).toBe(200);
      const cancelBody = await cancelRes.json();
      expect(cancelBody.data.status).toBe('CANCEL_REQUESTED');

      // 4. 해지 취소 (재활성화)
      const reactRes = await request.post(
        `${API_URL}/subscriptions/${subId}/reactivate`,
        { headers: { Authorization: `Bearer ${flowToken}` } }
      );
      expect(reactRes.status()).toBe(200);
      const reactBody = await reactRes.json();
      expect(reactBody.data.status).toBe('ACTIVE');
    });
  });
});
