/**
 * 발자국 (Foot-Print) E2E 테스트 공통 데이터 상수
 * 모든 테스트 파일에서 이 파일을 import하여 사용한다.
 */

// ─── 테스트 사용자 ────────────────────────────────────────────────────────────

export const TEST_USER = {
  email: 'e2e-test@footprint.dev',
  password: 'Test1234!',
  nickname: 'E2E테스터',
} as const;

/** 두 번째 사용자 (타인 장소 접근 예외 테스트용) */
export const TEST_USER_2 = {
  email: 'e2e-test2@footprint.dev',
  password: 'Test1234!',
  nickname: 'E2E테스터2',
} as const;

// ─── 샘플 장소 ────────────────────────────────────────────────────────────────

/**
 * 기본 샘플 장소 (필수 필드 + 선택 필드 포함)
 * categoryIds 의 실제 값은 테스트 환경의 기본 카테고리 ID를 사용한다.
 * global.setup.ts 에서 카테고리 목록 조회 후 동적으로 교체할 수 있다.
 */
export const TEST_PLACE = {
  name: '스타벅스 강남점',
  address: '서울특별시 강남구 강남대로 390',
  latitude: 37.4979,
  longitude: 127.0276,
  visitedAt: '2026-05-01',
  rating: 4,
  memo: '커피가 맛있었다',
  tags: ['커피', '카페'],
  /** 장소 등록 API 요청 시 사용 (기본 카테고리 맛집 ID: 1) */
  categoryIds: [1],
} as const;

/** 필수 필드만 포함한 최소 장소 데이터 */
export const TEST_PLACE_MINIMAL = {
  name: 'E2E 최소 테스트 장소',
  latitude: 37.5665,
  longitude: 126.978,
  visitedAt: '2026-05-02',
  categoryIds: [1],
} as const;

/** 장소 수정 테스트용 업데이트 데이터 */
export const TEST_PLACE_UPDATED = {
  name: 'E2E 수정된 장소명',
  visitedAt: '2026-04-30',
  memo: 'E2E 수정된 메모 내용',
  rating: 5,
} as const;

// ─── 샘플 카테고리 ───────────────────────────────────────────────────────────

export const TEST_CATEGORY = {
  name: 'E2E테스트카테고리',
  color: '#FF5733',
  icon: '🧪',
} as const;

export const TEST_CATEGORY_UPDATED = {
  name: 'E2E수정된카테고리',
  color: '#4CAF50',
} as const;

// ─── API Base URL ─────────────────────────────────────────────────────────────

export const API_BASE_URL = 'http://localhost:8080/api/v1';

// ─── 페이지 URL ───────────────────────────────────────────────────────────────

export const ROUTES = {
  login: '/login',
  signup: '/signup',
  map: '/map',
  places: '/places',
  placesNew: '/places/new',
  stats: '/stats',
  categories: '/categories',
} as const;

// ─── 유효성 검사 경계값 ───────────────────────────────────────────────────────

export const BOUNDARY = {
  /** 장소명 최대 100자 */
  placeNameMax: 'A'.repeat(100),
  /** 장소명 101자 (초과값) */
  placeNameOver: 'A'.repeat(101),
  /** 메모 최대 2000자 */
  memoMax: 'A'.repeat(2000),
  /** 미래 방문일 (오늘 + 1일) */
  futureDateVisitedAt: '2030-01-01',
  /** 위도 최솟값 경계 */
  latitudeMin: -90.0,
  /** 위도 최댓값 경계 */
  latitudeMax: 90.0,
  /** 위도 초과값 */
  latitudeOver: 91.0,
  /** 경도 초과값 */
  longitudeOver: 181.0,
} as const;
