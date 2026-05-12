import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { STALE_TIME } from '@/lib/constants';
import {
  mockHoldings,
  mockMarketSummary,
  mockPortfolio,
  mockRecommendations,
  mockSignals,
} from '@/lib/mocks/data';
import type { Holding, MarketSummary, PortfolioSummary } from '@/types/portfolio';
import type { Recommendation } from '@/types/recommendation';
import type { Signal } from '@/types/signal';

import { USE_MOCK, mockDelay } from './_mock-helpers';

/** 대시보드 KPI + 보유 + 시장 요약 + 시그널 + 추천주 (병렬 호출용 훅 모음) */

export function usePortfolioSummary() {
  return useQuery<PortfolioSummary>({
    queryKey: queryKeys.portfolio.summary(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockPortfolio);
      return api.get<PortfolioSummary>('/portfolios/summary');
    },
    staleTime: STALE_TIME.DEFAULT,
  });
}

export function useHoldings() {
  return useQuery<Holding[]>({
    queryKey: queryKeys.portfolio.holdings(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockHoldings);
      return api.get<Holding[]>('/portfolios/holdings');
    },
    staleTime: STALE_TIME.DEFAULT,
  });
}

export function useMarketSummary() {
  return useQuery<MarketSummary>({
    queryKey: queryKeys.dashboard.market(),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockMarketSummary);
      return api.get<MarketSummary>('/market/summary');
    },
    staleTime: 5_000,
    refetchInterval: 5_000,
  });
}

export function useActiveSignals(limit = 5) {
  return useQuery<Signal[]>({
    queryKey: queryKeys.signals.list({ active: true, limit }),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockSignals);
      return api.get<Signal[]>('/signals/active', { params: { limit } });
    },
    staleTime: STALE_TIME.REALTIME_QUOTE,
  });
}

export function useTopRecommendations(limit = 5) {
  return useQuery<Recommendation[]>({
    queryKey: queryKeys.recommendations.list({ top: limit }),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockRecommendations.slice(0, limit));
      return api.get<Recommendation[]>('/recommendations/top', { params: { limit } });
    },
    staleTime: 60_000,
  });
}
