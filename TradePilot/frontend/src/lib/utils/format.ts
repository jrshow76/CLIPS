/**
 * 통화/수익률/거래량 한글 포맷 유틸.
 * - 상승=빨강, 하락=파랑 컨벤션 일관 처리.
 * - 모든 숫자 표시는 tabular-nums 클래스와 함께 사용 권장.
 */

const KRW = new Intl.NumberFormat('ko-KR');

export function formatCurrency(value: number | null | undefined, suffix = '원'): string {
  if (value == null || Number.isNaN(value)) return '-';
  return `${KRW.format(Math.trunc(value))}${suffix}`;
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return '-';
  return value.toLocaleString('ko-KR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** 거래량/거래대금 한글 단위 (조/억/만) */
export function formatVolumeKR(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '-';
  const v = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (v >= 1e12) return `${sign}${(v / 1e12).toFixed(2)}조`;
  if (v >= 1e8) return `${sign}${(v / 1e8).toFixed(2)}억`;
  if (v >= 1e4) return `${sign}${(v / 1e4).toFixed(1)}만`;
  return `${sign}${KRW.format(v)}`;
}

/** 수익률(%): + / - 부호와 화살표를 함께 반환 */
export function formatPct(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return '-';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(digits)}%`;
}

/** 원화 손익: 부호 포함 */
export function formatPnl(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '-';
  const sign = value > 0 ? '+' : '';
  return `${sign}${KRW.format(Math.trunc(value))}`;
}

/**
 * 등락에 따른 색상 클래스 결정.
 * - Designer의 .text-up / .text-down / .text-flat 클래스를 그대로 사용.
 */
export function pnlClass(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value) || value === 0) return 'text-flat';
  return value > 0 ? 'text-up' : 'text-down';
}

/** 화살표 기호 (색맹 접근성: 색상 단독 사용 금지) */
export function pnlArrow(value: number | null | undefined): string {
  if (value == null || value === 0) return '·';
  return value > 0 ? '▲' : '▼';
}

/** 종목 코드 정규화: 6자리 0-padding */
export function normalizeStockCode(code: string): string {
  return code.padStart(6, '0');
}
