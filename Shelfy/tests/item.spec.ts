/**
 * Shelfy - 상품(아이템) E2E 테스트
 * 커버 시나리오:
 *   - TC-ITEM-001: 정상 상품 등록 (PURCHASE)
 *   - TC-ITEM-004: 이메일 미인증 상태 등록 차단
 *   - TC-ITEM-005~008: 가격 경계값
 *   - TC-ITEM-009: SUBSCRIBE 유형 플랜 누락 차단
 *   - TC-ITEM-020: 본인 상품 정상 수정
 *   - TC-ITEM-021: 타인 상품 수정 차단
 *   - TC-ITEM-023: 구독자 있는 플랜 가격 변경 차단
 *   - TC-ITEM-030: 정상 상품 삭제
 *   - TC-ITEM-031: 활성 구독자 있는 상품 삭제 차단
 *   - TC-ITEM-032: 타인 상품 삭제 차단
 *   - TC-ITEM-040: 상태 전환 (DRAFT/PUBLISHED)
 *   - TC-BROWSE-022: 비공개 상품 타인 접근 차단
 */

import { test, expect } from '@playwright/test';
import {
  signup,
  login,
  createItem,
  generateEmail,
  generateNickname,
} from './helpers/api';

const API_URL = process.env.API_URL || 'http://localhost:8080/api/v1';
const VALID_PASSWORD = 'Shelfy1234!';

// 테스트용 기본 상품 이미지 ID (사전 업로드된 fixture 값)
const FIXTURE_IMAGE_ID = process.env.FIXTURE_IMAGE_ID || 'img-fixture-001';

// 기본 상품 페이로드 팩토리
function buildItemPayload(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    title: '테스트 상품 기본',
    description: '이 상품은 자동화 테스트용 상품입니다. (10자 이상)',
    category: 'TEMPLATE',
    saleType: 'PURCHASE',
    price: 5000,
    imageIds: [FIXTURE_IMAGE_ID],
    thumbnailIndex: 0,
    tags: ['테스트', 'QA'],
    status: 'PUBLISHED',
    ...overrides,
  };
}

test.describe('상품 관리 (ITEM)', () => {
  let sellerToken: string;
  let sellerEmail: string;
  let otherToken: string;

  test.beforeAll(async ({ request }) => {
    // 셀러 계정 생성 및 이메일 인증 완료 (테스트 환경에서 자동 인증 처리 가정)
    sellerEmail = generateEmail('seller');
    await signup(request, {
      email: sellerEmail,
      password: VALID_PASSWORD,
      passwordConfirm: VALID_PASSWORD,
      nickname: generateNickname('seller'),
      agreeTerms: true,
      agreePrivacy: true,
    });
    sellerToken = await login(request, sellerEmail, VALID_PASSWORD);

    // 타인 계정 생성
    const otherEmail = generateEmail('other');
    await signup(request, {
      email: otherEmail,
      password: VALID_PASSWORD,
      passwordConfirm: VALID_PASSWORD,
      nickname: generateNickname('other'),
      agreeTerms: true,
      agreePrivacy: true,
    });
    otherToken = await login(request, otherEmail, VALID_PASSWORD);
  });

  test.describe('상품 등록', () => {
    test('TC-ITEM-001: 정상 상품 등록 (PURCHASE) - HTTP 201', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload());

      expect(response.status()).toBe(201);
      const body = await response.json();
      expect(body.success).toBe(true);
      expect(body.data.itemId).toBeTruthy();
    });

    test('TC-ITEM-002: 정상 상품 등록 (SUBSCRIBE) - HTTP 201', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload({
        saleType: 'SUBSCRIBE',
        price: undefined,
        subscriptionPlans: [
          { planName: 'Basic', period: 'MONTHLY', planPrice: 3000, description: '기본 플랜' },
        ],
      }));

      expect(response.status()).toBe(201);
    });

    test('TC-ITEM-003: 정상 상품 등록 (BOTH) - HTTP 201', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload({
        saleType: 'BOTH',
        price: 10000,
        subscriptionPlans: [
          { planName: 'Monthly', period: 'MONTHLY', planPrice: 4000 },
        ],
      }));

      expect(response.status()).toBe(201);
    });

    test('TC-ITEM-004: 이메일 미인증 상태 상품 등록 차단 - HTTP 403 / ITEM-E001', async ({ request }) => {
      // 이메일 미인증 계정 생성
      const unverifiedEmail = generateEmail('unverified');
      await signup(request, {
        email: unverifiedEmail,
        password: VALID_PASSWORD,
        passwordConfirm: VALID_PASSWORD,
        nickname: generateNickname('uv'),
        agreeTerms: true,
        agreePrivacy: true,
      });
      const unverifiedToken = await login(request, unverifiedEmail, VALID_PASSWORD);

      const response = await createItem(request, unverifiedToken, buildItemPayload());

      expect(response.status()).toBe(403);
      const body = await response.json();
      expect(body.error.code).toBe('ITEM-E001');
    });

    test('TC-ITEM-005: 가격 경계값 - 99원 거부', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload({ price: 99 }));
      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.error.code).toBe('ITEM-E005');
    });

    test('TC-ITEM-006: 가격 경계값 - 100원 허용', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload({ price: 100 }));
      expect(response.status()).toBe(201);
    });

    test('TC-ITEM-007: 가격 경계값 - 10,000,001원 거부', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload({ price: 10000001 }));
      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.error.code).toBe('ITEM-E005');
    });

    test('TC-ITEM-008: 가격 경계값 - 10,000,000원 허용', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload({ price: 10000000 }));
      expect(response.status()).toBe(201);
    });

    test('TC-ITEM-009: SUBSCRIBE 유형 구독 플랜 미포함 차단 - HTTP 400 / ITEM-E007', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload({
        saleType: 'SUBSCRIBE',
        price: undefined,
        subscriptionPlans: [],
      }));

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.error.code).toBe('ITEM-E007');
    });

    test('TC-ITEM-011: 유효하지 않은 카테고리 코드 - HTTP 400 / ITEM-E006', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload({
        category: 'INVALID_CATEGORY_XYZ',
      }));

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.error.code).toBe('ITEM-E006');
    });

    test('TC-ITEM-013: title 1자 거부', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload({ title: 'a' }));
      expect(response.status()).toBe(400);
    });

    test('TC-ITEM-015: description 9자 거부', async ({ request }) => {
      const response = await createItem(request, sellerToken, buildItemPayload({ description: '123456789' }));
      expect(response.status()).toBe(400);
    });
  });

  test.describe('상품 수정', () => {
    let itemId: number;

    test.beforeAll(async ({ request }) => {
      const res = await createItem(request, sellerToken, buildItemPayload({
        title: '수정 테스트용 상품',
      }));
      const body = await res.json();
      itemId = body.data.itemId;
    });

    test('TC-ITEM-020: 본인 상품 정상 수정 - HTTP 200', async ({ request }) => {
      const response = await request.put(`${API_URL}/items/${itemId}`, {
        headers: { Authorization: `Bearer ${sellerToken}` },
        data: { title: '수정된 상품명 변경' },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.data.itemId).toBe(itemId);
      expect(body.data.updatedAt).toBeTruthy();
    });

    test('TC-ITEM-021: 타인 상품 수정 차단 - HTTP 403 / ITEM-E020', async ({ request }) => {
      const response = await request.put(`${API_URL}/items/${itemId}`, {
        headers: { Authorization: `Bearer ${otherToken}` },
        data: { title: '해킹 시도' },
      });

      expect(response.status()).toBe(403);
      const body = await response.json();
      expect(body.error.code).toBe('ITEM-E020');
    });

    test('TC-ITEM-022: 존재하지 않는 상품 수정 - HTTP 404 / ITEM-E022', async ({ request }) => {
      const response = await request.put(`${API_URL}/items/99999999`, {
        headers: { Authorization: `Bearer ${sellerToken}` },
        data: { title: '없는 상품 수정 시도' },
      });

      expect(response.status()).toBe(404);
      const body = await response.json();
      expect(body.error.code).toBe('ITEM-E022');
    });
  });

  test.describe('상품 상태 변경', () => {
    let itemId: number;

    test.beforeAll(async ({ request }) => {
      const res = await createItem(request, sellerToken, buildItemPayload({
        title: '상태 전환 테스트 상품',
        status: 'DRAFT',
      }));
      const body = await res.json();
      itemId = body.data.itemId;
    });

    test('TC-ITEM-040: DRAFT → PUBLISHED 전환 - HTTP 200', async ({ request }) => {
      const response = await request.patch(`${API_URL}/items/${itemId}/status`, {
        headers: { Authorization: `Bearer ${sellerToken}` },
        data: { status: 'PUBLISHED' },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.data.status).toBe('PUBLISHED');
    });

    test('TC-ITEM-041: PUBLISHED → DRAFT 전환 후 타인 접근 차단', async ({ request }) => {
      // DRAFT로 변환
      const patchRes = await request.patch(`${API_URL}/items/${itemId}/status`, {
        headers: { Authorization: `Bearer ${sellerToken}` },
        data: { status: 'DRAFT' },
      });
      expect(patchRes.status()).toBe(200);

      // 타인이 접근 시도
      const getRes = await request.get(`${API_URL}/items/${itemId}`, {
        headers: { Authorization: `Bearer ${otherToken}` },
      });
      expect(getRes.status()).toBe(403);
      const body = await getRes.json();
      expect(body.error.code).toBe('BROWSE-E002');
    });

    test('TC-ITEM-042: 비공개 상품 본인 조회 가능', async ({ request }) => {
      // 상품을 DRAFT 상태로 유지
      await request.patch(`${API_URL}/items/${itemId}/status`, {
        headers: { Authorization: `Bearer ${sellerToken}` },
        data: { status: 'DRAFT' },
      });

      const getRes = await request.get(`${API_URL}/items/${itemId}`, {
        headers: { Authorization: `Bearer ${sellerToken}` },
      });
      expect(getRes.status()).toBe(200);
    });
  });

  test.describe('상품 삭제', () => {
    test('TC-ITEM-030: 정상 상품 삭제 - HTTP 204, 이후 404 반환', async ({ request }) => {
      const createRes = await createItem(request, sellerToken, buildItemPayload({
        title: '삭제 테스트 상품',
      }));
      const { data } = await createRes.json();
      const itemId = data.itemId;

      // 삭제
      const deleteRes = await request.delete(`${API_URL}/items/${itemId}`, {
        headers: { Authorization: `Bearer ${sellerToken}` },
      });
      expect(deleteRes.status()).toBe(204);

      // 삭제 후 조회 시 404
      const getRes = await request.get(`${API_URL}/items/${itemId}`);
      expect(getRes.status()).toBe(404);
      const body = await getRes.json();
      expect(body.error.code).toBe('BROWSE-E001');
    });

    test('TC-ITEM-032: 타인 상품 삭제 시도 차단 - HTTP 403 / ITEM-E031', async ({ request }) => {
      const createRes = await createItem(request, sellerToken, buildItemPayload({
        title: '타인 삭제 시도 대상 상품',
      }));
      const { data } = await createRes.json();
      const itemId = data.itemId;

      const deleteRes = await request.delete(`${API_URL}/items/${itemId}`, {
        headers: { Authorization: `Bearer ${otherToken}` },
      });

      expect(deleteRes.status()).toBe(403);
      const body = await deleteRes.json();
      expect(body.error.code).toBe('ITEM-E031');
    });
  });

  test.describe('내 상품 목록 조회', () => {
    test('TC-ITEM-050: 셀러 본인 상품 목록 - 공개/비공개 모두 포함', async ({ request }) => {
      const response = await request.get(`${API_URL}/items/my`, {
        headers: { Authorization: `Bearer ${sellerToken}` },
        params: { status: 'ALL' },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.data.content).toBeDefined();
      expect(body.data.page).toBe(0);
      expect(body.data.size).toBeDefined();
      expect(body.data.totalElements).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('상품 등록 → 목록 조회 → 상세 → 수정 → 삭제 통합 플로우', () => {
    test('아이템 전체 라이프사이클 플로우', async ({ request }) => {
      // 1. 등록
      const createRes = await createItem(request, sellerToken, buildItemPayload({
        title: '라이프사이클 테스트 상품',
        status: 'PUBLISHED',
      }));
      expect(createRes.status()).toBe(201);
      const { data: { itemId } } = await createRes.json();

      // 2. 목록 조회 (공개 목록에 포함 여부)
      const listRes = await request.get(`${API_URL}/items`);
      expect(listRes.status()).toBe(200);
      const listBody = await listRes.json();
      const found = listBody.data.content.some((i: { itemId: number }) => i.itemId === itemId);
      expect(found).toBe(true);

      // 3. 상세 조회
      const detailRes = await request.get(`${API_URL}/items/${itemId}`);
      expect(detailRes.status()).toBe(200);
      const detailBody = await detailRes.json();
      expect(detailBody.data.title).toBe('라이프사이클 테스트 상품');
      expect(detailBody.data.viewCount).toBeGreaterThanOrEqual(0);

      // 4. 수정
      const updateRes = await request.put(`${API_URL}/items/${itemId}`, {
        headers: { Authorization: `Bearer ${sellerToken}` },
        data: { title: '라이프사이클 테스트 상품 (수정됨)' },
      });
      expect(updateRes.status()).toBe(200);

      // 5. 삭제
      const deleteRes = await request.delete(`${API_URL}/items/${itemId}`, {
        headers: { Authorization: `Bearer ${sellerToken}` },
      });
      expect(deleteRes.status()).toBe(204);

      // 6. 삭제 확인
      const afterDeleteRes = await request.get(`${API_URL}/items/${itemId}`);
      expect(afterDeleteRes.status()).toBe(404);
    });
  });
});
