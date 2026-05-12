import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { makeMockCandles } from '@/lib/mocks/data';
import { toast } from '@/stores/notification-store';
import type {
  BacktestJob,
  BacktestRequest,
  BacktestResult,
} from '@/types/backtest';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useStartBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: BacktestRequest) => {
      if (USE_MOCK)
        return mockDelay<BacktestJob>({
          job_id: `bt_${Date.now()}`,
          status: 'QUEUED',
          progress: 0,
        });
      return api.post<BacktestJob>('/backtest', payload);
    },
    onSuccess: () => {
      toast.success('백테스트가 시작되었습니다.');
      qc.invalidateQueries({ queryKey: queryKeys.backtest.all });
    },
  });
}

export function useBacktestJob(jobId: string | undefined) {
  return useQuery<BacktestJob>({
    queryKey: jobId ? queryKeys.backtest.job(jobId) : ['backtest', 'job', 'idle'],
    queryFn: async () => {
      if (!jobId) throw new Error('jobId required');
      if (USE_MOCK)
        return mockDelay<BacktestJob>({
          job_id: jobId,
          status: 'DONE',
          progress: 100,
        });
      return api.get<BacktestJob>(`/backtest/${jobId}`);
    },
    enabled: !!jobId,
    refetchInterval: (q) => (q.state.data?.status === 'RUNNING' ? 1500 : false),
  });
}

export function useBacktestResult(jobId: string | undefined) {
  return useQuery<BacktestResult>({
    queryKey: jobId ? queryKeys.backtest.result(jobId) : ['backtest', 'result', 'idle'],
    queryFn: async () => {
      if (!jobId) throw new Error('jobId required');
      if (USE_MOCK) {
        const candles = makeMockCandles(10_000_000, 120);
        const equity_curve = candles.map((c) => ({ ts: c.ts, equity: c.close }));
        return mockDelay<BacktestResult>({
          job_id: jobId,
          status: 'DONE',
          total_return_pct: 18.4,
          cagr_pct: 14.2,
          mdd_pct: -8.7,
          sharpe: 1.42,
          win_rate: 58.3,
          trades: 124,
          equity_curve,
        });
      }
      return api.get<BacktestResult>(`/backtest/${jobId}/result`);
    },
    enabled: !!jobId,
  });
}
