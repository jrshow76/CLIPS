/**
 * TanStack Query Key 단일 출처.
 * - 형태: ['domain', 'action', ...params]
 * - 변경/필터 mutation 후 `queryClient.invalidateQueries({ queryKey: queryKeys.<domain>.all })` 형태로 무효화.
 */

export const queryKeys = {
  auth: {
    me: () => ['auth', 'me'] as const,
  },
  dashboard: {
    summary: () => ['dashboard', 'summary'] as const,
    market: () => ['dashboard', 'market'] as const,
  },
  portfolio: {
    holdings: () => ['portfolio', 'holdings'] as const,
    summary: () => ['portfolio', 'summary'] as const,
  },
  stocks: {
    all: ['stocks'] as const,
    search: (q: string) => ['stocks', 'search', q] as const,
    detail: (code: string) => ['stocks', 'detail', code] as const,
    quote: (code: string) => ['stocks', 'quote', code] as const,
    candles: (code: string, interval: string) =>
      ['stocks', 'candles', code, interval] as const,
    orderbook: (code: string) => ['stocks', 'orderbook', code] as const,
  },
  recommendations: {
    all: ['recommendations'] as const,
    list: (filter?: Record<string, unknown>) =>
      ['recommendations', 'list', filter ?? {}] as const,
    detail: (code: string) => ['recommendations', 'detail', code] as const,
  },
  signals: {
    all: ['signals'] as const,
    list: (filter?: Record<string, unknown>) =>
      ['signals', 'list', filter ?? {}] as const,
    detail: (id: string) => ['signals', 'detail', id] as const,
  },
  orders: {
    all: ['orders'] as const,
    list: (filter?: Record<string, unknown>) => ['orders', 'list', filter ?? {}] as const,
    detail: (id: string) => ['orders', 'detail', id] as const,
  },
  strategies: {
    all: ['strategies'] as const,
    list: () => ['strategies', 'list'] as const,
    detail: (id: string) => ['strategies', 'detail', id] as const,
  },
  sectors: {
    all: ['sectors'] as const,
    list: () => ['sectors', 'list'] as const,
    detail: (code: string) => ['sectors', 'detail', code] as const,
  },
  backtest: {
    all: ['backtest'] as const,
    job: (jobId: string) => ['backtest', 'job', jobId] as const,
    result: (jobId: string) => ['backtest', 'result', jobId] as const,
  },
  reports: {
    pnl: (period: string) => ['reports', 'pnl', period] as const,
  },
  settings: {
    me: () => ['settings', 'me'] as const,
  },
};
