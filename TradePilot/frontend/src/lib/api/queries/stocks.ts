import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { STALE_TIME } from '@/lib/constants';
import { makeMockCandles } from '@/lib/mocks/data';
import type { Candle, CandleInterval, Quote, Stock } from '@/types/stock';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useStockDetail(code: string | undefined) {
  return useQuery<Stock>({
    queryKey: code ? queryKeys.stocks.detail(code) : ['stocks', 'detail', 'idle'],
    queryFn: async () => {
      if (!code) throw new Error('code required');
      if (USE_MOCK) {
        return mockDelay<Stock>({
          code,
          name: code === '005930' ? '삼성전자' : '종목명',
          market: 'KOSPI',
          sector: '전기·전자',
        });
      }
      return api.get<Stock>(`/stocks/${code}`);
    },
    enabled: !!code,
    staleTime: STALE_TIME.MASTER,
  });
}

export function useQuote(code: string | undefined) {
  return useQuery<Quote>({
    queryKey: code ? queryKeys.stocks.quote(code) : ['stocks', 'quote', 'idle'],
    queryFn: async () => {
      if (!code) throw new Error('code required');
      if (USE_MOCK) {
        const base = 82_500;
        return mockDelay<Quote>({
          code,
          price: base,
          change: 2_300,
          change_pct: 2.87,
          volume: 12_345_678,
          ts: Date.now(),
        });
      }
      return api.get<Quote>(`/stocks/${code}/quote`);
    },
    enabled: !!code,
    staleTime: STALE_TIME.REALTIME_QUOTE,
    refetchInterval: STALE_TIME.REALTIME_QUOTE,
  });
}

export function useCandles(
  code: string | undefined,
  interval: CandleInterval = 'D',
  options?: { from?: string; to?: string },
) {
  return useQuery<Candle[]>({
    queryKey: code ? queryKeys.stocks.candles(code, interval) : ['stocks', 'candles', 'idle'],
    queryFn: async () => {
      if (!code) throw new Error('code required');
      if (USE_MOCK) {
        const seed = code === '005930' ? 82_500 : 100_000;
        return mockDelay(makeMockCandles(seed, 90), 150);
      }
      return api.get<Candle[]>(`/stocks/${code}/candles`, {
        params: { interval, ...options },
      });
    },
    enabled: !!code,
    staleTime: STALE_TIME.CANDLE,
  });
}
