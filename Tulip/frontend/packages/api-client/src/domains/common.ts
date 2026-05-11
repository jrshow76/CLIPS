/**
 * 도메인 공통 타입.
 *
 * 본 Phase의 백엔드(member-service, tenant-service, code-policy-service)는
 * 페이지 응답을 다음 평탄 구조로 반환할 것으로 가정한다:
 *
 *   { items: T[], page: number, size: number, total: number }
 *
 * 추후 envelope의 `meta.page`(offset/cursor)와 통합될 수 있다.
 */

export interface FlatOffsetPage<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
}

export interface OffsetQuery {
  page?: number;
  size?: number;
  sort?: string | string[];
}

/** 도메인 query string에서 undefined/null 키를 제거 */
export function compactQuery(input: object): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(input)) {
    if (v === undefined || v === null || v === '') continue;
    out[k] = v;
  }
  return out;
}
