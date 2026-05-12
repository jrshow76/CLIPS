/**
 * dashboard 도메인 모듈
 *
 * Phase 1-D 단계에서는 백엔드 통계 API가 미존재(예정: Phase 2)이므로
 * mock 모드 우선으로 동작한다. 실제 API 명세 확정 시 fetcher만 교체한다.
 *
 * 가정 API:
 *   GET /api/v1/dashboard/summary?libraryId
 *   GET /api/v1/dashboard/loan-trends?range=7|14|30&libraryId
 *   GET /api/v1/dashboard/top-members?limit&libraryId
 *   GET /api/v1/dashboard/overdue-risk?libraryId
 *   GET /api/v1/dashboard/activities?limit&libraryId
 */
import { useQuery, type UseQueryOptions } from '@tanstack/react-query';

import { useApiClient } from '../context';
import type { ApiError } from '../errors';
import { isMockMode, mockDelay } from '../mock';

import { compactQuery } from './common';

// ───────────────────────────── 타입 ─────────────────────────────

export type TrendDirection = 'up' | 'down' | 'flat';

export interface KpiMetric {
  /** 지표 키 (loans_active / overdue / new_members / reservations) */
  key: string;
  /** 한글 라벨 */
  label: string;
  /** 표시 값 (정수) */
  value: number;
  /** 비교 기준 대비 변화량 (양/음수) */
  delta?: number;
  /** delta 단위: 절대수 또는 퍼센트 */
  deltaUnit?: 'count' | 'percent';
  trend: TrendDirection;
  /** 의미적 색상 — danger면 빨강, success면 초록 */
  tone?: 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'info';
  /** sparkline용 7-point 데이터(있을 때) */
  sparkline?: number[];
}

export type AlertSeverity = 'info' | 'warning' | 'danger';

export interface DashboardAlert {
  id: string;
  severity: AlertSeverity;
  title: string;
  description?: string;
  /** 클릭 시 이동 경로 */
  href?: string;
  /** 발생 시각 (ISO) */
  occurredAt: string;
}

export interface LoanTrendPoint {
  /** YYYY-MM-DD */
  date: string;
  loans: number;
  returns: number;
  overdue: number;
}

export interface MemberTypeDistribution {
  type: 'ADULT' | 'YOUTH' | 'CHILD' | 'STAFF' | 'GUEST';
  label: string;
  count: number;
}

export interface DashboardSummary {
  kpis: KpiMetric[];
  alerts: DashboardAlert[];
  /** 회원 유형 분포 (도넛용) */
  memberTypeDistribution: MemberTypeDistribution[];
  /** 데이터 생성 시각 */
  generatedAt: string;
}

export interface TopMember {
  memberId: string;
  memberNumber: string;
  name: string;
  libraryName: string;
  /** 이번 달 대출 건수 */
  loans: number;
  /** 현재 대출 중 */
  active: number;
}

export interface OverdueRiskRow {
  loanId: string;
  memberName: string;
  memberNumber: string;
  bookTitle: string;
  /** 반납 예정일 (ISO date) */
  dueDate: string;
  /** 임박 정도: -3..0 = 임박, 양수 = 이미 연체일수 */
  daysUntilDue: number;
}

export type ActivityType =
  | 'member.registered'
  | 'library.created'
  | 'code.updated'
  | 'loan.checkout'
  | 'loan.return'
  | 'reservation.created'
  | 'system';

export interface ActivityEvent {
  id: string;
  type: ActivityType;
  message: string;
  actorName?: string;
  /** 컨텍스트(도서관·도메인) */
  contextLabel?: string;
  occurredAt: string;
}

export interface DashboardQuery {
  libraryId?: string;
}

export interface LoanTrendsQuery {
  range?: 7 | 14 | 30;
  libraryId?: string;
}

// ───────────────────────────── Query Keys ─────────────────────────────

export const dashboardKeys = {
  all: ['dashboard'] as const,
  summary: (q: DashboardQuery) => [...dashboardKeys.all, 'summary', q] as const,
  loanTrends: (q: LoanTrendsQuery) => [...dashboardKeys.all, 'loan-trends', q] as const,
  topMembers: (q: { limit?: number; libraryId?: string }) =>
    [...dashboardKeys.all, 'top-members', q] as const,
  overdueRisk: (q: DashboardQuery) => [...dashboardKeys.all, 'overdue-risk', q] as const,
  activities: (q: { limit?: number; libraryId?: string }) =>
    [...dashboardKeys.all, 'activities', q] as const,
};

// ───────────────────────────── Mock 생성기 ─────────────────────────────

/** 시드 기반 의사 난수 — 같은 입력에는 같은 출력(렌더 안정성). */
function seedRandom(seed: number): () => number {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function formatDateUTC(d: Date): string {
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(
    d.getUTCDate(),
  ).padStart(2, '0')}`;
}

function pastDate(daysAgo: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - daysAgo);
  d.setUTCHours(9, 0, 0, 0);
  return d.toISOString();
}

function buildMockSummary(q: DashboardQuery): DashboardSummary {
  // libraryId 시드로 안정적인 mock
  const seed =
    (q.libraryId ?? 'all').split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0) + 17;
  const rnd = seedRandom(seed);
  const sparkline = (base: number, scale: number) =>
    Array.from({ length: 7 }, () => Math.round(base + (rnd() - 0.5) * scale));

  const loansActive = 320 + Math.round(rnd() * 80);
  const overdue = 12 + Math.round(rnd() * 20);
  const newMembers = 28 + Math.round(rnd() * 30);
  const reservations = 45 + Math.round(rnd() * 25);

  return {
    kpis: [
      {
        key: 'loans_active',
        label: '대출 중',
        value: loansActive,
        delta: 12,
        deltaUnit: 'percent',
        trend: 'up',
        tone: 'primary',
        sparkline: sparkline(loansActive / 7, 18),
      },
      {
        key: 'overdue',
        label: '연체',
        value: overdue,
        delta: 2,
        deltaUnit: 'count',
        trend: 'up',
        tone: 'danger',
        sparkline: sparkline(overdue, 6),
      },
      {
        key: 'new_members',
        label: '신규 회원(이번달)',
        value: newMembers,
        delta: 18,
        deltaUnit: 'percent',
        trend: 'up',
        tone: 'success',
        sparkline: sparkline(newMembers / 4, 5),
      },
      {
        key: 'reservations',
        label: '예약 대기',
        value: reservations,
        delta: -3,
        deltaUnit: 'percent',
        trend: 'down',
        tone: 'info',
        sparkline: sparkline(reservations / 5, 6),
      },
    ],
    alerts: [
      {
        id: 'alt_overdue',
        severity: 'danger',
        title: '연체 임박 7건',
        description: '오늘 반납 예정 중 미반납 가능성이 높습니다.',
        href: '/circulation/overdue',
        occurredAt: pastDate(0),
      },
      {
        id: 'alt_stock',
        severity: 'warning',
        title: '인기 자료 재고 부족',
        description: '"디자인 시스템 입문" 외 3건 추가 발주 권장.',
        href: '/acquisition',
        occurredAt: pastDate(1),
      },
      {
        id: 'alt_facility',
        severity: 'info',
        title: '시설 점검 예정',
        description: '5/14(목) 02:00 — 분관A 정기 점검 안내.',
        href: '/facility/libraries',
        occurredAt: pastDate(2),
      },
    ],
    memberTypeDistribution: [
      { type: 'ADULT', label: '성인', count: 1820 },
      { type: 'YOUTH', label: '청소년', count: 640 },
      { type: 'CHILD', label: '어린이', count: 420 },
      { type: 'STAFF', label: '직원', count: 35 },
      { type: 'GUEST', label: '게스트', count: 90 },
    ],
    generatedAt: new Date().toISOString(),
  };
}

function buildMockLoanTrends(q: LoanTrendsQuery): LoanTrendPoint[] {
  const range = q.range ?? 14;
  const seed =
    (q.libraryId ?? 'all').split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0) + range;
  const rnd = seedRandom(seed);
  const out: LoanTrendPoint[] = [];
  for (let i = range - 1; i >= 0; i--) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - i);
    const weekend = d.getUTCDay() === 0 || d.getUTCDay() === 6;
    const base = weekend ? 280 : 360;
    const loans = Math.max(50, Math.round(base + (rnd() - 0.5) * 90));
    const returns = Math.max(40, Math.round(base * 0.92 + (rnd() - 0.5) * 90));
    const overdue = Math.max(0, Math.round(8 + (rnd() - 0.5) * 12));
    out.push({ date: formatDateUTC(d), loans, returns, overdue });
  }
  return out;
}

function buildMockTopMembers(limit = 5): TopMember[] {
  const base: Omit<TopMember, 'loans' | 'active'>[] = [
    { memberId: 'mbr_001', memberNumber: 'M2024-0001', name: '홍길동', libraryName: '중앙도서관' },
    { memberId: 'mbr_002', memberNumber: 'M2024-0002', name: '김영희', libraryName: '분관A' },
    { memberId: 'mbr_003', memberNumber: 'M2025-0003', name: '박철수', libraryName: '중앙도서관' },
    { memberId: 'mbr_004', memberNumber: 'M2025-0010', name: '이수정', libraryName: '분관B' },
    { memberId: 'mbr_005', memberNumber: 'M2024-0017', name: '최민호', libraryName: '중앙도서관' },
    { memberId: 'mbr_006', memberNumber: 'M2025-0021', name: '정유진', libraryName: '분관A' },
  ];
  return base.slice(0, limit).map((m, i) => ({
    ...m,
    loans: 32 - i * 3,
    active: Math.max(1, 6 - i),
  }));
}

function buildMockOverdueRisk(): OverdueRiskRow[] {
  return [
    {
      loanId: 'ln_1001',
      memberName: '김영희',
      memberNumber: 'M2024-0002',
      bookTitle: '데이터 분석가의 기초',
      dueDate: pastDate(-1),
      daysUntilDue: 1,
    },
    {
      loanId: 'ln_1002',
      memberName: '박철수',
      memberNumber: 'M2025-0003',
      bookTitle: '디자인 시스템 입문',
      dueDate: pastDate(0),
      daysUntilDue: 0,
    },
    {
      loanId: 'ln_1003',
      memberName: '이수정',
      memberNumber: 'M2025-0010',
      bookTitle: '실전 TypeScript',
      dueDate: pastDate(1),
      daysUntilDue: -1,
    },
    {
      loanId: 'ln_1004',
      memberName: '최민호',
      memberNumber: 'M2024-0017',
      bookTitle: '한강 소설집',
      dueDate: pastDate(3),
      daysUntilDue: -3,
    },
  ];
}

function buildMockActivities(limit = 10): ActivityEvent[] {
  const base: ActivityEvent[] = [
    {
      id: 'act_1',
      type: 'member.registered',
      message: '신규 회원 가입',
      actorName: '정유진',
      contextLabel: '중앙도서관',
      occurredAt: pastDate(0),
    },
    {
      id: 'act_2',
      type: 'loan.checkout',
      message: '대출 처리 완료 — 도서 5건',
      actorName: '카운터 사서',
      contextLabel: '분관A',
      occurredAt: pastDate(0),
    },
    {
      id: 'act_3',
      type: 'loan.return',
      message: '반납 처리 — 도서 3건',
      actorName: '셀프 반납기',
      contextLabel: '중앙도서관',
      occurredAt: pastDate(0),
    },
    {
      id: 'act_4',
      type: 'code.updated',
      message: '코드 정책 변경: BOOK_STATUS',
      actorName: '관리자',
      contextLabel: '코드 관리',
      occurredAt: pastDate(1),
    },
    {
      id: 'act_5',
      type: 'reservation.created',
      message: '예약 신청 — "한강 소설집"',
      actorName: '홍길동',
      contextLabel: '중앙도서관',
      occurredAt: pastDate(1),
    },
    {
      id: 'act_6',
      type: 'library.created',
      message: '분관C 등록',
      actorName: '시설팀',
      contextLabel: 'Tulip+',
      occurredAt: pastDate(2),
    },
    {
      id: 'act_7',
      type: 'system',
      message: '월간 통계 배치 완료',
      contextLabel: 'system',
      occurredAt: pastDate(2),
    },
    {
      id: 'act_8',
      type: 'member.registered',
      message: '신규 회원 가입',
      actorName: '강도윤',
      contextLabel: '분관B',
      occurredAt: pastDate(3),
    },
    {
      id: 'act_9',
      type: 'loan.checkout',
      message: '대출 처리 완료 — 도서 2건',
      actorName: '카운터 사서',
      contextLabel: '분관A',
      occurredAt: pastDate(3),
    },
    {
      id: 'act_10',
      type: 'code.updated',
      message: '코드 정책 변경: MEMBER_TYPE',
      actorName: '관리자',
      contextLabel: '코드 관리',
      occurredAt: pastDate(4),
    },
  ];
  return base.slice(0, limit);
}

// ───────────────────────────── Hooks ─────────────────────────────

export function useDashboardSummaryQuery(
  params: DashboardQuery = {},
  options?: Omit<UseQueryOptions<DashboardSummary, ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<DashboardSummary, ApiError>({
    queryKey: dashboardKeys.summary(params),
    queryFn: () => {
      if (isMockMode()) return mockDelay(buildMockSummary(params), 400);
      return client.get<DashboardSummary>('/dashboard/summary', {
        query: compactQuery(params),
      });
    },
    staleTime: 30_000,
    ...options,
  });
}

export function useLoanTrendsQuery(
  params: LoanTrendsQuery = {},
  options?: Omit<UseQueryOptions<LoanTrendPoint[], ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<LoanTrendPoint[], ApiError>({
    queryKey: dashboardKeys.loanTrends(params),
    queryFn: () => {
      if (isMockMode()) return mockDelay(buildMockLoanTrends(params), 350);
      return client.get<LoanTrendPoint[]>('/dashboard/loan-trends', {
        query: compactQuery(params),
      });
    },
    staleTime: 60_000,
    ...options,
  });
}

export function useTopMembersQuery(
  params: { limit?: number; libraryId?: string } = {},
  options?: Omit<UseQueryOptions<TopMember[], ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<TopMember[], ApiError>({
    queryKey: dashboardKeys.topMembers(params),
    queryFn: () => {
      if (isMockMode()) return mockDelay(buildMockTopMembers(params.limit ?? 5), 300);
      return client.get<TopMember[]>('/dashboard/top-members', {
        query: compactQuery(params),
      });
    },
    staleTime: 60_000,
    ...options,
  });
}

export function useOverdueRiskQuery(
  params: DashboardQuery = {},
  options?: Omit<UseQueryOptions<OverdueRiskRow[], ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<OverdueRiskRow[], ApiError>({
    queryKey: dashboardKeys.overdueRisk(params),
    queryFn: () => {
      if (isMockMode()) return mockDelay(buildMockOverdueRisk(), 300);
      return client.get<OverdueRiskRow[]>('/dashboard/overdue-risk', {
        query: compactQuery(params),
      });
    },
    staleTime: 30_000,
    ...options,
  });
}

export function useRecentActivitiesQuery(
  params: { limit?: number; libraryId?: string } = {},
  options?: Omit<UseQueryOptions<ActivityEvent[], ApiError>, 'queryKey' | 'queryFn'>,
) {
  const client = useApiClient();
  return useQuery<ActivityEvent[], ApiError>({
    queryKey: dashboardKeys.activities(params),
    queryFn: () => {
      if (isMockMode()) return mockDelay(buildMockActivities(params.limit ?? 10), 300);
      return client.get<ActivityEvent[]>('/dashboard/activities', {
        query: compactQuery(params),
      });
    },
    staleTime: 15_000,
    ...options,
  });
}

// ───────────────────────────── Internal helpers (test-friendly) ─────────────────────────────

export const __mockBuilders = {
  buildMockSummary,
  buildMockLoanTrends,
  buildMockTopMembers,
  buildMockOverdueRisk,
  buildMockActivities,
};
