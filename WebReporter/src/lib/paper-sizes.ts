import type { PaperSize, Orientation } from './types';

// 용지 크기 (mm) - portrait 기준
export const PAPER_SIZES: Record<PaperSize, { width: number; height: number; label: string }> = {
  A3:     { width: 297,   height: 420,   label: 'A3 (297×420mm)' },
  A4:     { width: 210,   height: 297,   label: 'A4 (210×297mm)' },
  A5:     { width: 148,   height: 210,   label: 'A5 (148×210mm)' },
  Letter: { width: 215.9, height: 279.4, label: 'Letter (216×279mm)' },
  Legal:  { width: 215.9, height: 355.6, label: 'Legal (216×356mm)' },
};

/** 방향을 반영한 실제 width/height 반환 (mm) */
export function getPageDimensions(
  size: PaperSize,
  orientation: Orientation,
): { width: number; height: number } {
  const { width, height } = PAPER_SIZES[size];
  if (orientation === 'landscape') {
    return { width: height, height: width };
  }
  return { width, height };
}

/** mm → point 변환 (PDF 생성용, 1pt = 0.3528mm) */
export function mmToPt(mm: number): number {
  return mm * 2.8346;
}

/** mm → px 변환 (화면 표시용, 1mm = 3.7795px @ 96dpi) */
export function mmToPx(mm: number, scale = 1): number {
  return mm * 3.7795 * scale;
}

/** px → mm 변환 */
export function pxToMm(px: number, scale = 1): number {
  return px / (3.7795 * scale);
}
