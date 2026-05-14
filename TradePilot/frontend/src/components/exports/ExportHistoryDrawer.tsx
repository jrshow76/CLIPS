'use client';

import { Download, History, X } from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal';
import {
  useDownloadExport,
  useExportHistory,
  type ExportJob,
} from '@/lib/api/queries/exports';

/**
 * 익스포트 이력 사이드 드로어. 실제 사이드 드로어 컴포넌트가 없으므로
 * 큰 size 의 Modal 로 대체한다. 모바일에서는 풀스크린에 가깝게 표시된다.
 */
export function ExportHistoryDrawer() {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useExportHistory(1, 20);
  const download = useDownloadExport();

  return (
    <>
      <Button
        variant="ghost"
        leftIcon={<History className="h-4 w-4" />}
        onClick={() => setOpen(true)}
      >
        익스포트 이력
      </Button>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="최근 익스포트 이력"
        size="lg"
        footer={
          <Button variant="ghost" onClick={() => setOpen(false)}>
            닫기
          </Button>
        }
      >
        {isLoading && <p className="text-sm text-subtle">불러오는 중...</p>}

        {data && data.items.length === 0 && (
          <p className="text-sm text-subtle">아직 익스포트 이력이 없습니다.</p>
        )}

        {data && data.items.length > 0 && (
          <ul className="stack gap-2">
            {data.items.map((j: ExportJob) => (
              <li
                key={j.export_id}
                className="row justify-between items-center p-2 border rounded"
              >
                <div className="stack gap-0.5">
                  <div className="row gap-2 items-center">
                    <span className="fw-semibold text-sm">{humanType(j.job_type)}</span>
                    <Badge variant="info">{j.format}</Badge>
                    <StatusBadge status={j.status} />
                  </div>
                  <span className="text-xs text-subtle">
                    {new Date(j.created_at).toLocaleString('ko-KR')}
                    {j.row_count != null ? ` · ${j.row_count.toLocaleString('ko-KR')}건` : ''}
                  </span>
                </div>
                {j.status === 'DONE' && (
                  <Button
                    size="sm"
                    variant="outline"
                    leftIcon={<Download className="h-4 w-4" />}
                    onClick={() => download.mutate(j.export_id)}
                  >
                    다운로드
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Modal>
    </>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'DONE') return <Badge variant="success">완료</Badge>;
  if (status === 'FAILED' || status === 'EXPIRED') return <Badge variant="danger">{status}</Badge>;
  if (status === 'CANCELED') return <Badge variant="warning">취소</Badge>;
  return <Badge variant="info">{status}</Badge>;
}

function humanType(t: string): string {
  switch (t) {
    case 'ORDERS':
      return '거래내역';
    case 'PNL':
      return '일별 손익';
    case 'BACKTEST':
      return '백테스트';
    case 'SIGNALS':
      return '시그널 이력';
    case 'POSITIONS':
      return '보유 종목';
    default:
      return t;
  }
}
