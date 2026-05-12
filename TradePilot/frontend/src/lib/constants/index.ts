import type { TradeMode } from '@/types/api';

/**
 * 라우트 경로 단일 출처.
 * docs/12_screen_flow.md, docs/22_frontend_structure.md §3 참조.
 */
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  SIGNUP: '/signup',
  PASSWORD_RESET: '/password-reset',
  DASHBOARD: '/dashboard',
  RECOMMENDATIONS: '/recommendations',
  RECOMMENDATION_DETAIL: (code: string) => `/recommendations/${code}`,
  CHART: (code: string) => `/chart/${code}`,
  SECTORS: '/sectors',
  SIGNALS: '/signals',
  AUTO_TRADING: '/auto-trading',
  REPORT: '/report',
  BACKTEST: '/backtest',
  BACKTEST_DETAIL: (jobId: string) => `/backtest/${jobId}`,
  SETTINGS: '/settings',
  NOT_FOUND: '/404',
} as const;

/** 매매 모드 라벨 */
export const TRADE_MODE_LABEL: Record<TradeMode, string> = {
  SIM: '시뮬',
  LIVE: '실거래',
};

export const TRADE_MODE_DESCRIPTION: Record<TradeMode, string> = {
  SIM: '가상 자금으로 안전하게 전략을 검증합니다.',
  LIVE: '실제 증권사 계좌로 주문이 전송됩니다.',
};

/**
 * 에러 코드 → 사용자 메시지 매핑.
 * docs/14_exception_policy.md §2 참조 (요약본).
 */
export const ERROR_MESSAGES: Record<string, string> = {
  // 공통 / 시스템
  E0001: '로그인이 필요합니다.',
  E0002: '권한이 없습니다.',
  E0003: '입력값을 확인해주세요.',
  E0004: '외부 시스템에서 일시적인 오류가 발생했습니다.',
  E0005: '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
  E0006: '매매 모드가 일치하지 않습니다. 모드를 재확인해주세요.',
  E0008: '요청이 너무 많습니다. 잠시 후 다시 시도해주세요.',
  E0009: '서비스가 점검 중입니다.',
  // 인증 / 모드
  E0011: 'OTP가 일치하지 않습니다.',
  E0013: '관리자 권한이 필요합니다.',
  E0016: 'LIVE 모드 사용이 허용되지 않은 계정입니다.',
  E0017: '다른 세션에서 매매 모드가 변경되었습니다.',
  // 주문
  E0021: '일일 매수 한도를 초과했습니다.',
  E0022: '중복 주문입니다.',
  E0023: '브로커 응답이 없습니다.',
  E0024: '주문 가능 수량을 초과했습니다.',
  E0026: '주문 가격이 허용 범위를 벗어났습니다.',
  E0027: '장 시간이 아닙니다.',
  E0028: '청산이 진행 중인 종목입니다.',
  // 백테스트
  E0031: '백테스트 작업이 만료되었습니다.',
  E0032: '백테스트 입력이 올바르지 않습니다.',
  E0033: '백테스트 실행 중 오류가 발생했습니다.',
  // 사용자
  E0051: '이미 가입된 이메일입니다.',
  E0052: '계정이 잠겼습니다. 잠시 후 다시 시도해주세요.',
  E0053: '인증 토큰이 만료되었습니다.',
  E0055: '비밀번호 정책을 만족하지 않습니다.',
  // 시세 / 시장
  E0061: '시세 데이터를 불러올 수 없습니다.',
  E0062: '종목을 찾을 수 없습니다.',
  E0063: '시세가 지연되고 있습니다.',
  // 외부 시스템
  E0071: '크레온 게이트웨이 연결에 실패했습니다.',
  E0072: '외부 응답 시간이 초과되었습니다.',
};

/** 한글 컬럼/메뉴 라벨 모음 (Designer 마크업과 일치) */
export const MENU_LABELS = {
  DASHBOARD: '대시보드',
  RECOMMENDATIONS: '추천주',
  CHART: '차트분석',
  SECTORS: '업종분석',
  SIGNALS: '매매 시그널',
  AUTO_TRADING: '자동매매',
  REPORT: '수익률 리포트',
  BACKTEST: '백테스트',
  SETTINGS: '설정',
  LOGOUT: '로그아웃',
} as const;

/** TanStack Query 기본 staleTime (ms) */
export const STALE_TIME = {
  REALTIME_QUOTE: 3_000,
  CANDLE: 60_000,
  MASTER: 60 * 60 * 1000, // 1h
  DEFAULT: 30_000,
} as const;

/** 페이지네이션 기본값 */
export const PAGE_DEFAULT = { PAGE: 1, SIZE: 20, MAX_SIZE: 100 } as const;
