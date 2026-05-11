/**
 * 도서관 6+1 도메인 메타데이터
 */

export type DomainCode = 'acq' | 'cat' | 'cir' | 'col' | 'acs' | 'fac' | 'opac';

export interface DomainMeta {
  code: DomainCode;
  /** 한글명 */
  name: string;
  /** 영문명 */
  englishName: string;
  /** 약어 (3글자) */
  abbr: string;
  /** 컬러 hex (Designer 가이드 Domain Accent) */
  color: string;
  /** API base path */
  basePath: string;
  /** 관리자 메뉴 경로 */
  adminRoute: string;
}

export const DOMAINS: Record<DomainCode, DomainMeta> = {
  acq: {
    code: 'acq',
    name: '수서',
    englishName: 'Acquisition',
    abbr: 'ACQ',
    color: '#F97316',
    basePath: '/api/v1/acq',
    adminRoute: '/acquisition',
  },
  cat: {
    code: 'cat',
    name: '목록',
    englishName: 'Catalog',
    abbr: 'CAT',
    color: '#8B5CF6',
    basePath: '/api/v1/cat',
    adminRoute: '/cataloging',
  },
  cir: {
    code: 'cir',
    name: '열람',
    englishName: 'Circulation',
    abbr: 'CIR',
    color: '#0EA5E9',
    basePath: '/api/v1/cir',
    adminRoute: '/circulation',
  },
  col: {
    code: 'col',
    name: '장서',
    englishName: 'Collection',
    abbr: 'COL',
    color: '#84CC16',
    basePath: '/api/v1/col',
    adminRoute: '/collection',
  },
  acs: {
    code: 'acs',
    name: '출입',
    englishName: 'Access',
    abbr: 'ACS',
    color: '#EF4444',
    basePath: '/api/v1/acs',
    adminRoute: '/access',
  },
  fac: {
    code: 'fac',
    name: '시설',
    englishName: 'Facility',
    abbr: 'FAC',
    color: '#14B8A6',
    basePath: '/api/v1/fac',
    adminRoute: '/facility',
  },
  opac: {
    code: 'opac',
    name: 'OPAC',
    englishName: 'OPAC',
    abbr: 'OPC',
    color: '#DB2777',
    basePath: '/api/v1/opac',
    adminRoute: '/opac',
  },
};

export const ADMIN_DOMAINS: DomainCode[] = ['acq', 'cat', 'cir', 'col', 'acs', 'fac'];
