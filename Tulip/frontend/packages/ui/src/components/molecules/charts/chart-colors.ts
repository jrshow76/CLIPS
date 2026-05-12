/**
 * 차트 시리즈 컬러 팔레트.
 *
 * 디자인 토큰 도메인 컬러를 참조하되, CSS 변수가 다크 모드에서 자동 전환되도록 var() 형태로 둔다.
 */
export const SERIES_COLORS = [
  'var(--color-primary-500, #db2777)',
  'var(--color-info, #0284c7)',
  'var(--color-warning, #d97706)',
  'var(--color-success, #16a34a)',
  'var(--color-danger, #dc2626)',
  '#8b5cf6',
  '#14b8a6',
  '#f97316',
  '#6366f1',
  '#84cc16',
] as const;

export function seriesColor(index: number): string {
  return SERIES_COLORS[index % SERIES_COLORS.length];
}
