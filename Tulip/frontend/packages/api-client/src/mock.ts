/**
 * Mock 모드 가드.
 *
 * 백엔드 서비스가 미완성인 Phase 1-C 단계에서는
 * `NEXT_PUBLIC_USE_MOCK=true`로 빌드된 앱에서 도메인 hook이
 * 실제 fetch 대신 mock 응답을 반환하도록 한다.
 *
 * 운영/스테이징에서는 반드시 `false`(또는 미지정) 상태여야 한다.
 */
export function isMockMode(): boolean {
  // Next.js는 NEXT_PUBLIC_ 접두 변수를 빌드 타임에 inline 치환한다.
  // 브라우저에서도 안전하게 process.env에 접근할 수 있도록 가드.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const proc = (globalThis as any).process as { env?: Record<string, string | undefined> } | undefined;
  const v = proc?.env?.NEXT_PUBLIC_USE_MOCK;
  return v === 'true' || v === '1';
}

/** Mock 응답에 약간의 지연을 부여해 로딩 상태 UX를 확인할 수 있게 함 */
export function mockDelay<T>(value: T, ms = 200): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), ms);
  });
}
