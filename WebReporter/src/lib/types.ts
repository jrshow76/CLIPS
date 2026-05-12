// 용지 크기
export type PaperSize = 'A3' | 'A4' | 'A5' | 'Letter' | 'Legal';
// 방향
export type Orientation = 'portrait' | 'landscape';

// 여백 (단위: mm)
export interface Margins {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

// 페이지 설정
export interface PageSettings {
  size: PaperSize;
  orientation: Orientation;
  margins: Margins;
}

// 요소 타입
export type ElementType = 'text' | 'rect' | 'line' | 'image' | 'ellipse';

// 요소 기본 인터페이스 (단위: mm)
export interface BaseElement {
  id: string;
  type: ElementType;
  x: number;
  y: number;
  width: number;
  height: number;
  locked: boolean;
  zIndex: number;
  name: string;
}

// 텍스트 요소
export interface TextElement extends BaseElement {
  type: 'text';
  content: string;
  fontSize: number;
  fontFamily: string;
  fontWeight: 'normal' | 'bold';
  fontStyle: 'normal' | 'italic';
  textDecoration: 'none' | 'underline';
  textAlign: 'left' | 'center' | 'right' | 'justify';
  color: string;
  backgroundColor: string;
  borderColor: string;
  borderWidth: number;
  paddingTop: number;
  paddingBottom: number;
  paddingLeft: number;
  paddingRight: number;
  lineHeight: number;
}

// 사각형 요소
export interface RectElement extends BaseElement {
  type: 'rect';
  fillColor: string;
  strokeColor: string;
  strokeWidth: number;
  borderRadius: number;
  opacity: number;
}

// 라인 요소
export interface LineElement extends BaseElement {
  type: 'line';
  color: string;
  strokeWidth: number;
  // 라인 방향: horizontal=가로, vertical=세로, diagonal-down=우하향, diagonal-up=우상향
  direction: 'horizontal' | 'vertical' | 'diagonal-down' | 'diagonal-up';
  dashed: boolean;
}

// 이미지 요소
export interface ImageElement extends BaseElement {
  type: 'image';
  src: string;
  objectFit: 'contain' | 'cover' | 'fill' | 'none';
  opacity: number;
}

// 타원 요소
export interface EllipseElement extends BaseElement {
  type: 'ellipse';
  fillColor: string;
  strokeColor: string;
  strokeWidth: number;
  opacity: number;
}

export type ReportElement =
  | TextElement
  | RectElement
  | LineElement
  | ImageElement
  | EllipseElement;

// 리포트 밴드 (크로닉스/유비레포트 스타일)
export type BandType =
  | 'reportHeader'
  | 'pageHeader'
  | 'detail'
  | 'pageFooter'
  | 'reportFooter';

export interface ReportBand {
  type: BandType;
  label: string;
  height: number; // mm
  visible: boolean;
  elements: ReportElement[];
}

// 리포트 템플릿
export interface ReportTemplate {
  id: string;
  name: string;
  pageSettings: PageSettings;
  // 밴드 없이 자유 배치 모드
  elements: ReportElement[];
}

// 선택 핸들 방향
export type ResizeHandle =
  | 'nw' | 'n' | 'ne'
  | 'w'  |       'e'
  | 'sw' | 's' | 'se';

// 기본 페이지 설정
export const DEFAULT_PAGE_SETTINGS: PageSettings = {
  size: 'A4',
  orientation: 'portrait',
  margins: { top: 10, bottom: 10, left: 10, right: 10 },
};
