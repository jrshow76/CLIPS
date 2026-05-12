/**
 * Mock 모드 헬퍼.
 * - NEXT_PUBLIC_USE_MOCK=true이면 실제 API 호출 대신 mock 데이터를 반환.
 * - 백엔드 가용 시 환경변수만 false로 바꿔 실 API로 전환.
 */
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true';

export function mockDelay<T>(value: T, ms = 200): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}
