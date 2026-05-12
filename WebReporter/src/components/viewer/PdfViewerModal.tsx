'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { X, Download, Printer, ZoomIn, ZoomOut, ChevronLeft, ChevronRight } from 'lucide-react';
import { pdf } from '@react-pdf/renderer';
import { ReportPdfDocument } from '@/lib/pdf-renderer';
import type { ReportTemplate } from '@/lib/types';

interface PdfViewerModalProps {
  template: ReportTemplate;
  onClose: () => void;
}

export default function PdfViewerModal({ template, onClose }: PdfViewerModalProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  const generatePdf = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const blob = await pdf(<ReportPdfDocument template={template} />).toBlob();
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);
    } catch (e) {
      console.error(e);
      setError('PDF 생성 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }, [template]);

  useEffect(() => {
    generatePdf();
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDownload = () => {
    if (!pdfUrl) return;
    const a = document.createElement('a');
    a.href = pdfUrl;
    a.download = `${template.name}.pdf`;
    a.click();
  };

  const handlePrint = () => {
    if (!pdfUrl) return;
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = pdfUrl;
    document.body.appendChild(iframe);
    iframe.onload = () => {
      iframe.contentWindow?.print();
      setTimeout(() => document.body.removeChild(iframe), 1000);
    };
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-gray-900/95 backdrop-blur-sm">
      {/* 헤더 */}
      <div className="flex items-center gap-3 px-4 h-12 bg-gray-800 border-b border-gray-700 flex-shrink-0">
        <span className="text-white font-semibold text-sm">{template.name} — PDF 미리보기</span>
        <div className="flex-1" />

        {/* 줌 */}
        <button
          className="p-1.5 rounded hover:bg-white/10 text-gray-300"
          onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))}
        >
          <ZoomOut size={16} />
        </button>
        <span className="text-xs text-gray-300 w-12 text-center">{Math.round(zoom * 100)}%</span>
        <button
          className="p-1.5 rounded hover:bg-white/10 text-gray-300"
          onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
        >
          <ZoomIn size={16} />
        </button>

        <div className="w-px h-5 bg-white/20 mx-1" />

        {/* 다운로드 */}
        <button
          className="flex items-center gap-1.5 px-3 h-8 rounded bg-green-600 hover:bg-green-500 text-white text-sm transition-colors"
          onClick={handleDownload}
          disabled={!pdfUrl}
        >
          <Download size={14} /> 저장
        </button>

        {/* 인쇄 */}
        <button
          className="flex items-center gap-1.5 px-3 h-8 rounded bg-yellow-600 hover:bg-yellow-500 text-white text-sm transition-colors"
          onClick={handlePrint}
          disabled={!pdfUrl}
        >
          <Printer size={14} /> 인쇄
        </button>

        {/* 닫기 */}
        <button
          className="p-1.5 rounded hover:bg-white/10 text-gray-300 ml-2"
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </div>

      {/* 본문 */}
      <div className="flex-1 overflow-auto flex items-start justify-center p-6 bg-gray-800">
        {loading && (
          <div className="flex flex-col items-center justify-center h-full text-gray-300">
            <div className="w-10 h-10 border-4 border-accent border-t-transparent rounded-full animate-spin mb-4" />
            <span className="text-sm">PDF 생성 중...</span>
          </div>
        )}
        {error && (
          <div className="text-red-400 text-sm mt-20">{error}</div>
        )}
        {pdfUrl && !loading && (
          <div
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: 'top center',
              transition: 'transform 0.2s',
            }}
          >
            <iframe
              src={pdfUrl}
              className="bg-white shadow-2xl"
              style={{
                width:  '210mm',
                height: '297mm',
                border: 'none',
                display: 'block',
              }}
              title="PDF 미리보기"
            />
          </div>
        )}
      </div>
    </div>
  );
}
