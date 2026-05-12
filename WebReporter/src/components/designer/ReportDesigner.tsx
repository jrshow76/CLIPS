'use client';

import React, { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import DesignerToolbar from './DesignerToolbar';
import DesignerCanvas  from './DesignerCanvas';
import PropertyPanel   from './PropertyPanel';
import PageSettingsPanel from './PageSettingsPanel';
import LayerPanel      from './LayerPanel';
import { useReportStore } from '@/store/useReportStore';
import { pdf } from '@react-pdf/renderer';
import { ReportPdfDocument } from '@/lib/pdf-renderer';

// PDF 뷰어는 dynamic import (SSR 제외)
const PdfViewerModal = dynamic(() => import('@/components/viewer/PdfViewerModal'), {
  ssr: false,
});

export default function ReportDesigner() {
  const { template, undo, redo, removeElements, selectedIds, duplicateElements, selectAll } =
    useReportStore();

  const [showPdfModal, setShowPdfModal] = useState(false);

  // 키보드 단축키
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return;

      const ctrl = e.ctrlKey || e.metaKey;
      if (ctrl && e.key === 'z') { e.preventDefault(); undo(); }
      if (ctrl && e.key === 'y') { e.preventDefault(); redo(); }
      if (ctrl && e.key === 'd') { e.preventDefault(); duplicateElements(selectedIds); }
      if (ctrl && e.key === 'a') { e.preventDefault(); selectAll(); }
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedIds.length > 0) { e.preventDefault(); removeElements(selectedIds); }
      }
    },
    [undo, redo, selectedIds, removeElements, duplicateElements, selectAll],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const handleDownloadPdf = async () => {
    try {
      const blob = await pdf(<ReportPdfDocument template={template} />).toBlob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `${template.name}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('PDF 저장 오류:', e);
      alert('PDF 저장 중 오류가 발생했습니다.');
    }
  };

  const handlePrint = async () => {
    try {
      const blob   = await pdf(<ReportPdfDocument template={template} />).toBlob();
      const url    = URL.createObjectURL(blob);
      const iframe = document.createElement('iframe');
      iframe.style.display = 'none';
      iframe.src = url;
      document.body.appendChild(iframe);
      iframe.onload = () => {
        iframe.contentWindow?.print();
        setTimeout(() => {
          document.body.removeChild(iframe);
          URL.revokeObjectURL(url);
        }, 2000);
      };
    } catch (e) {
      console.error('인쇄 오류:', e);
      alert('인쇄 중 오류가 발생했습니다.');
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-designer-bg">
      {/* 상단 툴바 */}
      <DesignerToolbar
        onPreviewPdf={() => setShowPdfModal(true)}
        onDownloadPdf={handleDownloadPdf}
        onPrint={handlePrint}
      />

      {/* 본문: 왼쪽 패널 + 캔버스 + 오른쪽 패널 */}
      <div className="flex flex-1 min-h-0">
        {/* 왼쪽: 페이지 설정 + 레이어 */}
        <div className="w-52 flex-shrink-0 bg-panel-bg border-r border-gray-200 flex flex-col overflow-y-auto">
          <PageSettingsPanel />
          <LayerPanel />
        </div>

        {/* 캔버스 */}
        <DesignerCanvas />

        {/* 오른쪽: 속성 패널 */}
        <PropertyPanel />
      </div>

      {/* PDF 미리보기 모달 */}
      {showPdfModal && (
        <PdfViewerModal
          template={template}
          onClose={() => setShowPdfModal(false)}
        />
      )}
    </div>
  );
}
