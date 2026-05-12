'use client';

import React from 'react';
import {
  Type, Square, Minus, Image, Circle,
  Undo2, Redo2, ZoomIn, ZoomOut, Grid3x3,
  Trash2, Copy, Layers, Printer, FileDown, Eye,
  ChevronUp, ChevronDown,
} from 'lucide-react';
import { useReportStore } from '@/store/useReportStore';
import {
  createTextElement, createRectElement,
  createLineElement, createImageElement, createEllipseElement,
} from '@/lib/element-defaults';
import { getPageDimensions } from '@/lib/paper-sizes';

interface ToolbarProps {
  onPreviewPdf: () => void;
  onDownloadPdf: () => void;
  onPrint: () => void;
}

export default function DesignerToolbar({ onPreviewPdf, onDownloadPdf, onPrint }: ToolbarProps) {
  const {
    template, selectedIds, zoom,
    past, future,
    showGrid, snapToGrid,
    addElement, removeElements, duplicateElements,
    bringForward, sendBackward, bringToFront, sendToBack,
    setZoom, undo, redo,
    toggleGrid, toggleSnapToGrid,
  } = useReportStore();

  const { pageSettings } = template;
  const { width: pw, height: ph } = getPageDimensions(pageSettings.size, pageSettings.orientation);

  const centerX = pw / 2 - 30;
  const centerY = ph / 2 - 10;

  const addText    = () => addElement(createTextElement(centerX, centerY));
  const addRect    = () => addElement(createRectElement(centerX, centerY));
  const addLine    = () => addElement(createLineElement(centerX, centerY));
  const addImage   = () => addElement(createImageElement(centerX, centerY));
  const addEllipse = () => addElement(createEllipseElement(centerX, centerY));

  const hasSel  = selectedIds.length > 0;
  const hasSingle = selectedIds.length === 1;

  const firstSel = hasSingle ? selectedIds[0] : null;

  const ZOOM_STEPS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3];
  const zoomIn  = () => {
    const next = ZOOM_STEPS.find((z) => z > zoom) ?? 3;
    setZoom(next);
  };
  const zoomOut = () => {
    const prev = [...ZOOM_STEPS].reverse().find((z) => z < zoom) ?? 0.25;
    setZoom(prev);
  };

  const btnBase =
    'flex items-center justify-center w-9 h-9 rounded hover:bg-white/10 transition-colors text-gray-200 disabled:opacity-30 disabled:cursor-not-allowed';
  const sepCls = 'w-px h-6 bg-white/20 mx-1';

  return (
    <div className="flex items-center gap-1 px-3 h-12 bg-toolbar-bg border-b border-white/10 flex-shrink-0 overflow-x-auto">
      {/* 요소 추가 */}
      <span className="text-xs text-gray-400 mr-1 whitespace-nowrap">추가</span>
      <button className={btnBase} onClick={addText}    title="텍스트 (T)"><Type   size={16} /></button>
      <button className={btnBase} onClick={addRect}    title="사각형"><Square  size={16} /></button>
      <button className={btnBase} onClick={addEllipse} title="타원">  <Circle  size={16} /></button>
      <button className={btnBase} onClick={addLine}    title="라인">  <Minus   size={16} /></button>
      <button className={btnBase} onClick={addImage}   title="이미지"><Image   size={16} /></button>

      <div className={sepCls} />

      {/* 실행 취소 / 다시 실행 */}
      <button className={btnBase} onClick={undo} disabled={past.length === 0}   title="실행 취소 (Ctrl+Z)"><Undo2  size={16} /></button>
      <button className={btnBase} onClick={redo} disabled={future.length === 0} title="다시 실행 (Ctrl+Y)"><Redo2  size={16} /></button>

      <div className={sepCls} />

      {/* 선택 요소 조작 */}
      <button className={btnBase} onClick={() => duplicateElements(selectedIds)} disabled={!hasSel} title="복제 (Ctrl+D)"><Copy   size={16} /></button>
      <button className={btnBase} onClick={() => removeElements(selectedIds)}    disabled={!hasSel} title="삭제 (Del)">  <Trash2 size={16} /></button>

      <div className={sepCls} />

      {/* 순서 변경 */}
      <span className="text-xs text-gray-400 whitespace-nowrap">순서</span>
      <button className={btnBase} onClick={() => firstSel && bringToFront(firstSel)} disabled={!hasSingle} title="맨 앞으로"><Layers     size={16} /></button>
      <button className={btnBase} onClick={() => firstSel && bringForward(firstSel)} disabled={!hasSingle} title="앞으로">  <ChevronUp  size={16} /></button>
      <button className={btnBase} onClick={() => firstSel && sendBackward(firstSel)} disabled={!hasSingle} title="뒤로">   <ChevronDown size={16} /></button>
      <button className={btnBase} onClick={() => firstSel && sendToBack(firstSel)}   disabled={!hasSingle} title="맨 뒤로"><Layers     size={16} className="rotate-180" /></button>

      <div className={sepCls} />

      {/* 표시 옵션 */}
      <button
        className={`${btnBase} ${showGrid ? 'bg-accent/30' : ''}`}
        onClick={toggleGrid} title="격자 표시"
      >
        <Grid3x3 size={16} />
      </button>
      <button
        className={`${btnBase} text-xs px-2 w-auto ${snapToGrid ? 'bg-accent/30' : ''}`}
        onClick={toggleSnapToGrid} title="격자 스냅"
      >
        스냅
      </button>

      <div className={sepCls} />

      {/* 줌 */}
      <button className={btnBase} onClick={zoomOut} title="축소"><ZoomOut size={16} /></button>
      <span className="text-xs text-gray-300 w-12 text-center">{Math.round(zoom * 100)}%</span>
      <button className={btnBase} onClick={zoomIn}  title="확대"><ZoomIn  size={16} /></button>

      <div className="flex-1" />

      {/* PDF / 출력 */}
      <button
        className="flex items-center gap-1.5 px-3 h-8 rounded bg-accent hover:bg-blue-500 text-white text-sm font-medium transition-colors"
        onClick={onPreviewPdf} title="PDF 미리보기"
      >
        <Eye size={14} /> 미리보기
      </button>
      <button
        className={`${btnBase} text-green-400`}
        onClick={onDownloadPdf} title="PDF 저장"
      >
        <FileDown size={16} />
      </button>
      <button
        className={`${btnBase} text-yellow-400`}
        onClick={onPrint} title="인쇄"
      >
        <Printer size={16} />
      </button>
    </div>
  );
}
