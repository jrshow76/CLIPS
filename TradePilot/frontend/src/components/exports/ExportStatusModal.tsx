'use client';

import { Download, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal';
import { Progress } from '@/components/ui/progress';
import {
  useCancelExport,
  useDownloadExport,
  useExportStatus,
} from '@/lib/api/queries/exports';

export interface ExportStatusModalProps {
  jobId: string;
  onClose: () => void;
}

/**
 * 익스포트 진행률 + 완료 시 다운로드 버튼.
 * 폴링은 useExportStatus 가 자동 처리(3초 간격, DONE/FAILED 에서 중단).
 */
export function ExportStatusModal({ jobId, onClose }: ExportStatusModalProps) {
  const { data, isLoading } = useExportStatus(jobId);
  const download = useDownloadExport();
  const cancel = useCancelExport();

  const status = data?.status;
  const progress = data?.progress_percent ?? 0;
  const isDone = status === 'DONE';
  const isFailed = status === 'FAILED' || status === 'EXPIRED' || status === 'CANCELED';
  const isInFlight = status === 'PENDING' || status === 'RUNNING';

  return (
    <Modal
      open
      onClose={onClose}
      title="익스포트 진행 상태"
      size="sm"
      footer={
        <div className="row gap-2 justify-end">
          {isInFlight && (
            <Button
              variant="ghost"
              leftIcon={<X className="h-4 w-4" />}
              onClick={() => cancel.mutate(jobId, { onSuccess: onClose })}
              disabled={cancel.isPending}
            >
              취소
            </Button>
          )}
          {isDone && (
            <Button
              leftIcon={<Download className="h-4 w-4" />}
              onClick={() => download.mutate(jobId)}
              disabled={download.isPending}
            >
              {download.isPending ? '준비 중...' : '다운로드'}
            </Button>
          )}
          <Button variant={isDone || isFailed ? 'primary' : 'ghost'} onClick={onClose}>
            닫기
          </Button>
        </div>
      }
    >
      <div className="stack gap-3">
        {isLoading && <p className="text-sm text-subtle">상태 확인 중...</p>}

        {data && (
          <>
            <div>
              <div className="row justify-between mb-1">
                <span className="fw-semibold text-sm">상태</span>
                <span className="text-sm">{statusLabel(status)}</span>
              </div>
              <Progress
                value={progress}
                variant={isFailed ? 'danger' : isDone ? 'success' : 'default'}
                label={isInFlight ? '처리 중' : isDone ? '완료' : isFailed ? '실패' : ''}
              />
            </div>

            {data.row_count != null && (
              <p className="text-xs text-subtle">
                행 수: {data.row_count.toLocaleString('ko-KR')}건
                {data.file_size_bytes
                  ? ` · 파일 크기: ${formatBytes(data.file_size_bytes)}`
                  : ''}
              </p>
            )}

            {isFailed && data.error_message && (
              <p className="text-xs text-down">오류: {data.error_message}</p>
            )}

            {isDone && (
              <p className="text-xs text-subtle">
                다운로드 링크는 1시간 동안 유효합니다. 만료된 경우 다시 다운로드 버튼을
                누르면 새 링크가 발급됩니다.
              </p>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}

function statusLabel(status: string | undefined): string {
  switch (status) {
    case 'PENDING':
      return '대기 중';
    case 'RUNNING':
      return '처리 중';
    case 'DONE':
      return '완료';
    case 'FAILED':
      return '실패';
    case 'EXPIRED':
      return '만료';
    case 'CANCELED':
      return '취소됨';
    default:
      return '-';
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}
