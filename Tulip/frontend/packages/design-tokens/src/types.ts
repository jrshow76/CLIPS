/**
 * 디자인 토큰 타입 정의
 */
export type ColorScale = '50' | '100' | '200' | '300' | '400' | '500' | '600' | '700' | '800' | '900';

export type SemanticVariant = 'success' | 'warning' | 'danger' | 'info';

export type DomainKey = 'acq' | 'cat' | 'cir' | 'col' | 'acs' | 'fac';

export type ThemeMode = 'light' | 'dark';

export interface TypographyStyle {
  size: string;
  lineHeight: string;
  weight: number;
  tracking?: string;
}
