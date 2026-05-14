'use client';

import { Download } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal';
import { Select } from '@/components/ui/select';
import { useRequestExport, type ExportFormat, type ExportJobType } from '@/lib/api/queries/exports';

import { ExportStatusModal } from './ExportStatusModal';

export interface ExportButtonProps {
  /** 익스포트 종류 */
  jobType: ExportJobType;
  /** 익스포트 시 함께 보낼 필터 파라미터 (기간/종목/run_id 등) */
  filterParams?: Record<string, unknown>;
  /** 버튼 라벨 (기본: "다운로드") */
  label?: string;
  /** 포맷 선택 UI 표시 여부 (기본 true). false 면 CSV 고정 */
  allowFormatSelect?: boolean;
  /** 버튼 variant */
  variant?: 'outline' | 'primary' | 'ghost';
  /** 비활성화 */
  disabled?: boolean;
}

/**
 * 익스포트 진입 버튼 + 포맷 선택 모달 + 진행 모달.
 *
 * 사용 예:
 *   <ExportButton jobType="ORDERS" filterParams={{from, to}} />
 */
export function ExportButton({
  jobType,
  filterParams,
  label = '다운로드',
  allowFormatSelect = true,
  variant = 'outline',
  disabled,
}: ExportButtonProps) {
  const [open, setOpen] = useState(false);
  const [format, setFormat] = useState<ExportFormat>('CSV');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const request = useRequestExport();

  function start() {
    request.mutate(
      { job_type: jobType, format, filter_params: filterParams ?? {} },
      {
        onSuccess: (data) => {
          setActiveJobId(data.export_id);
          setOpen(false);
        },
      },
    );
  }

  return (
    <>
      <Button
        variant={variant}
        leftIcon={<Download className="h-4 w-4" />}
        onClick={() => setOpen(true)}
        disabled={disabled || request.isPending}
      >
        {label}
      </Button>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={`${humanType(jobType)} 익스포트`}
        size="sm"
        footer={
          <div className="row gap-2 justify-end">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              취소
            </Button>
            <Button onClick={start} disabled={request.isPending}>
              {request.isPending ? '요청 중...' : '익스포트 시작'}
            </Button>
          </div>
        }
      >
        <div className="stack gap-3">
          <p className="text-sm text-subtle">
            선택한 데이터를 파일로 내려받습니다. 파일 생성에는 잠시 시간이 걸릴 수 있으며,
            다운로드 링크는 1시간 동안 유효합니다.
          </p>
          {allowFormatSelect && (
            <label className="stack gap-1 text-sm">
              <span className="fw-semibold">포맷</span>
              <Select
                value={format}
                onChange={(e) => setFormat(e.target.value as ExportFormat)}
              >
                <option value="CSV">CSV (한글 헤더, UTF-8 BOM)</option>
                <option value="XLSX">XLSX (다중 시트, 셀 포맷)</option>
              </Select>
            </label>
          )}
        </div>
      </Modal>

      {activeJobId && (
        <ExportStatusModal
          jobId={activeJobId}
          onClose={() => setActiveJobId(null)}
        />
      )}
    </>
  );
}

function humanType(t: ExportJobType): string {
  switch (t) {
    case 'ORDERS':
      return '거래내역';
    case 'PNL':
      return '일별 손익';
    case 'BACKTEST':
      return '백테스트 결과';
    case 'SIGNALS':
      return '시그널 이력';
    case 'POSITIONS':
      return '보유 종목';
  }
}
