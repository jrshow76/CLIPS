/**
 * 익스포트(CSV/XLSX) API 쿼리/뮤테이션.
 *
 * 흐름:
 *   1. useRequestExport — POST /exports → public_id 발급
 *   2. useExportStatus — GET  /exports/{id} 3초 폴링 (DONE/FAILED 시 중단)
 *   3. useDownloadExport — GET /exports/{id}/download → 사전서명 URL 즉시 새 탭 다운로드
 *   4. useExportHistory — GET /exports?page=N
 *   5. useCancelExport — DELETE /exports/{id}
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { toast } from '@/stores/notification-store';

export type ExportJobType = 'ORDERS' | 'PNL' | 'BACKTEST' | 'SIGNALS' | 'POSITIONS';
export type ExportFormat = 'CSV' | 'XLSX';
export type ExportStatus = 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED' | 'EXPIRED' | 'CANCELED';

export interface ExportRequestPayload {
  job_type: ExportJobType;
  format: ExportFormat;
  filter_params?: Record<string, unknown>;
}

export interface ExportRequestResponse {
  job_id: string;
  status: ExportStatus;
  export_id: string;
}

export interface ExportJob {
  export_id: string;
  job_type: ExportJobType;
  format: ExportFormat;
  status: ExportStatus;
  progress_percent: number;
  row_count: number | null;
  file_size_bytes: number | null;
  download_url: string | null;
  download_url_expires_at: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  expires_at: string | null;
}

export interface ExportDownload {
  export_id: string;
  download_url: string;
  expires_at: string;
}

export interface ExportHistoryPage {
  items: ExportJob[];
  page: number;
  size: number;
  total: number;
  has_next: boolean;
}

/** POST /exports — 신규 익스포트 잡 생성. */
export function useRequestExport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ExportRequestPayload) =>
      api.post<ExportRequestResponse>('/exports', payload),
    onSuccess: () => {
      toast.success('익스포트가 시작되었습니다. 잠시만 기다려 주세요.');
      qc.invalidateQueries({ queryKey: queryKeys.exports.all });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : '익스포트 요청에 실패했습니다.';
      toast.danger(msg);
    },
  });
}

/** GET /exports/{id} — 상태 3초 폴링 (DONE/FAILED/EXPIRED 시 자동 중단). */
export function useExportStatus(jobId: string | undefined, enabled = true) {
  return useQuery<ExportJob>({
    queryKey: jobId ? queryKeys.exports.status(jobId) : ['exports', 'status', 'idle'],
    queryFn: async () => {
      if (!jobId) throw new Error('jobId required');
      return api.get<ExportJob>(`/exports/${jobId}`);
    },
    enabled: !!jobId && enabled,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (!status) return 3000;
      // 완료/실패 상태에서는 폴링 중단
      if (status === 'DONE' || status === 'FAILED' || status === 'EXPIRED' || status === 'CANCELED') {
        return false;
      }
      return 3000;
    },
  });
}

/** GET /exports/{id}/download — 사전서명 URL 발급. 만료 시 자동 갱신. */
export function useDownloadExport() {
  return useMutation({
    mutationFn: (jobId: string) => api.get<ExportDownload>(`/exports/${jobId}/download`),
    onSuccess: (data) => {
      // 새 탭에서 다운로드 트리거
      if (typeof window !== 'undefined' && data.download_url) {
        window.open(data.download_url, '_blank', 'noopener,noreferrer');
      }
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : '다운로드 URL 발급에 실패했습니다.';
      toast.danger(msg);
    },
  });
}

/** GET /exports — 사용자 이력 페이지. */
export function useExportHistory(page = 1, size = 20) {
  return useQuery<ExportHistoryPage>({
    queryKey: queryKeys.exports.list(page),
    queryFn: () =>
      api.get<ExportHistoryPage>('/exports', { params: { page, size } }),
    staleTime: 30_000,
  });
}

/** DELETE /exports/{id} — 취소 또는 즉시 만료. */
export function useCancelExport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => api.delete<ExportJob>(`/exports/${jobId}`),
    onSuccess: () => {
      toast.success('익스포트를 취소했습니다.');
      qc.invalidateQueries({ queryKey: queryKeys.exports.all });
    },
  });
}
