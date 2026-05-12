'use client';

import React, { useRef, useCallback, useState, useEffect } from 'react';
import { useReportStore } from '@/store/useReportStore';
import { getPageDimensions, mmToPx, pxToMm } from '@/lib/paper-sizes';
import type { ReportElement, ResizeHandle } from '@/lib/types';

// ─── 요소 렌더러 ────────────────────────────────────────────────────────────

function RenderElement({ el, scale }: { el: ReportElement; scale: number }) {
  const px = (mm: number) => mmToPx(mm, scale);

  const style: React.CSSProperties = {
    position: 'absolute',
    left: px(el.x),
    top:  px(el.y),
    width:  px(el.width),
    height: px(el.height),
    zIndex: el.zIndex,
    boxSizing: 'border-box',
  };

  if (el.type === 'text') {
    return (
      <div
        style={{
          ...style,
          fontSize:       el.fontSize * scale,
          fontFamily:     el.fontFamily,
          fontWeight:     el.fontWeight,
          fontStyle:      el.fontStyle,
          textDecoration: el.textDecoration,
          textAlign:      el.textAlign,
          color:          el.color,
          background:     el.backgroundColor,
          border:         el.borderWidth > 0 ? `${el.borderWidth * scale}px solid ${el.borderColor}` : undefined,
          padding:        `${px(el.paddingTop)}px ${px(el.paddingRight)}px ${px(el.paddingBottom)}px ${px(el.paddingLeft)}px`,
          lineHeight:     el.lineHeight,
          overflow:       'hidden',
          whiteSpace:     'pre-wrap',
          wordBreak:      'break-word',
          pointerEvents:  'none',
          userSelect:     'none',
        }}
      >
        {el.content}
      </div>
    );
  }

  if (el.type === 'rect') {
    return (
      <div
        style={{
          ...style,
          background:   el.fillColor,
          border:       `${el.strokeWidth * scale}px solid ${el.strokeColor}`,
          borderRadius: el.borderRadius * scale,
          opacity:      el.opacity,
          pointerEvents: 'none',
        }}
      />
    );
  }

  if (el.type === 'ellipse') {
    return (
      <div
        style={{
          ...style,
          background:    el.fillColor,
          border:        `${el.strokeWidth * scale}px solid ${el.strokeColor}`,
          borderRadius:  '50%',
          opacity:       el.opacity,
          pointerEvents: 'none',
        }}
      />
    );
  }

  if (el.type === 'line') {
    const w = px(el.width);
    const h = px(el.height);
    const sw = el.strokeWidth * scale;
    const dash = el.dashed ? `${sw * 4},${sw * 2}` : undefined;

    let x1 = 0, y1 = 0, x2 = w, y2 = 0;
    if (el.direction === 'vertical')       { x1 = w/2; y1 = 0; x2 = w/2; y2 = h || px(50); }
    if (el.direction === 'diagonal-down')  { x2 = w; y2 = h; }
    if (el.direction === 'diagonal-up')    { y1 = h; x2 = w; y2 = 0; }

    return (
      <svg style={{ ...style, overflow: 'visible', pointerEvents: 'none' }}>
        <line
          x1={x1} y1={y1} x2={x2} y2={y2}
          stroke={el.color}
          strokeWidth={sw}
          strokeDasharray={dash}
        />
      </svg>
    );
  }

  if (el.type === 'image') {
    return (
      <div style={{ ...style, overflow: 'hidden', opacity: el.opacity, pointerEvents: 'none' }}>
        {el.src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={el.src} alt="image element"
            style={{ width: '100%', height: '100%', objectFit: el.objectFit }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gray-100 text-gray-400 text-xs border border-dashed border-gray-300">
            이미지
          </div>
        )}
      </div>
    );
  }

  return null;
}

// ─── 선택 핸들 ──────────────────────────────────────────────────────────────

const HANDLE_SIZE = 8;

function SelectionHandles({
  el, scale, onResize,
}: {
  el: ReportElement;
  scale: number;
  onResize: (handle: ResizeHandle, e: React.MouseEvent) => void;
}) {
  const px = (mm: number) => mmToPx(mm, scale);
  const x = px(el.x), y = px(el.y), w = px(el.width), h = px(el.height);

  const handles: Array<{ id: ResizeHandle; cx: number; cy: number; cursor: string }> = [
    { id: 'nw', cx: x,       cy: y,       cursor: 'nw-resize' },
    { id: 'n',  cx: x + w/2, cy: y,       cursor: 'n-resize' },
    { id: 'ne', cx: x + w,   cy: y,       cursor: 'ne-resize' },
    { id: 'w',  cx: x,       cy: y + h/2, cursor: 'w-resize' },
    { id: 'e',  cx: x + w,   cy: y + h/2, cursor: 'e-resize' },
    { id: 'sw', cx: x,       cy: y + h,   cursor: 'sw-resize' },
    { id: 's',  cx: x + w/2, cy: y + h,   cursor: 's-resize' },
    { id: 'se', cx: x + w,   cy: y + h,   cursor: 'se-resize' },
  ];

  return (
    <>
      {/* 선택 테두리 */}
      <div
        style={{
          position: 'absolute',
          left:   x - 1,
          top:    y - 1,
          width:  w + 2,
          height: h + 2,
          border: '2px solid #4f80ff',
          boxSizing: 'border-box',
          pointerEvents: 'none',
          zIndex: 9999,
        }}
      />
      {/* 핸들 */}
      {handles.map(({ id, cx, cy, cursor }) => (
        <div
          key={id}
          data-handle={id}
          onMouseDown={(e) => { e.stopPropagation(); onResize(id, e); }}
          style={{
            position:  'absolute',
            left:      cx - HANDLE_SIZE / 2,
            top:       cy - HANDLE_SIZE / 2,
            width:     HANDLE_SIZE,
            height:    HANDLE_SIZE,
            background: '#fff',
            border:    '2px solid #4f80ff',
            borderRadius: 2,
            cursor,
            zIndex:    10000,
          }}
        />
      ))}
    </>
  );
}

// ─── 메인 캔버스 ────────────────────────────────────────────────────────────

interface DragState {
  type: 'move' | 'resize';
  startX: number;
  startY: number;
  origElements: ReportElement[];
  handle?: ResizeHandle;
}

export default function DesignerCanvas() {
  const {
    template, selectedIds, zoom,
    showGrid, gridSize,
    selectElement, clearSelection,
    updateElement, saveSnapshot,
  } = useReportStore();

  const { pageSettings, elements } = template;
  const { width: pageW, height: pageH } = getPageDimensions(
    pageSettings.size, pageSettings.orientation,
  );

  const scale = zoom;
  const px = (mm: number) => mmToPx(mm, scale);

  const canvasRef = useRef<HTMLDivElement>(null);
  const dragRef   = useRef<DragState | null>(null);
  const [, forceUpdate] = useState(0);

  // 마우스 이동 핸들러
  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      const d = dragRef.current;
      if (!d) return;
      const dx = pxToMm(e.clientX - d.startX, scale);
      const dy = pxToMm(e.clientY - d.startY, scale);

      if (d.type === 'move') {
        d.origElements.forEach((orig) => {
          updateElement(orig.id, { x: orig.x + dx, y: orig.y + dy });
        });
      } else if (d.type === 'resize' && d.origElements.length === 1) {
        const orig = d.origElements[0];
        const handle = d.handle!;
        let { x, y, width, height } = orig;

        if (handle.includes('e')) width  = Math.max(5, orig.width  + dx);
        if (handle.includes('s')) height = Math.max(5, orig.height + dy);
        if (handle.includes('w')) { x = orig.x + dx; width  = Math.max(5, orig.width  - dx); }
        if (handle.includes('n')) { y = orig.y + dy; height = Math.max(5, orig.height - dy); }

        updateElement(orig.id, { x, y, width, height });
      }

      forceUpdate((n) => n + 1);
    },
    [scale, updateElement],
  );

  const handleMouseUp = useCallback(() => {
    if (dragRef.current) {
      saveSnapshot();
      dragRef.current = null;
    }
  }, [saveSnapshot]);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup',   handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup',   handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  // 요소 클릭/드래그 시작
  const handleElementMouseDown = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      const multi = e.shiftKey || e.ctrlKey || e.metaKey;
      selectElement(id, multi);

      const ids = multi
        ? useReportStore.getState().selectedIds.includes(id)
          ? useReportStore.getState().selectedIds
          : [...useReportStore.getState().selectedIds, id]
        : [id];

      const origElements = useReportStore.getState().template.elements
        .filter((el) => ids.includes(el.id))
        .map((el) => ({ ...el }));

      dragRef.current = {
        type: 'move',
        startX: e.clientX,
        startY: e.clientY,
        origElements,
      };
    },
    [selectElement],
  );

  // 리사이즈 핸들 드래그 시작
  const handleResizeStart = useCallback(
    (handle: ResizeHandle, e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      const el = elements.find((el) => el.id === id);
      if (!el) return;
      dragRef.current = {
        type: 'resize',
        startX: e.clientX,
        startY: e.clientY,
        origElements: [{ ...el }],
        handle,
      };
    },
    [elements],
  );

  // 캔버스 배경 클릭 → 선택 해제
  const handleCanvasClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === canvasRef.current || (e.target as HTMLElement).dataset.canvasBg) {
        clearSelection();
      }
    },
    [clearSelection],
  );

  const pagePxW = px(pageW);
  const pagePxH = px(pageH);

  // 격자 배경 이미지
  const gridBg = showGrid
    ? `repeating-linear-gradient(0deg, transparent, transparent ${px(gridSize) - 1}px, #d0d0d0 ${px(gridSize)}px),
       repeating-linear-gradient(90deg, transparent, transparent ${px(gridSize) - 1}px, #d0d0d0 ${px(gridSize)}px)`
    : undefined;

  const sortedElements = [...elements].sort((a, b) => a.zIndex - b.zIndex);

  return (
    <div
      className="relative overflow-auto flex-1 flex items-start justify-center bg-designer-bg"
      style={{ minHeight: 0 }}
    >
      <div className="py-8 px-8">
        {/* 용지 */}
        <div
          ref={canvasRef}
          onMouseDown={handleCanvasClick}
          style={{
            position: 'relative',
            width:   pagePxW,
            height:  pagePxH,
            background: gridBg || '#fff',
            boxShadow: '0 4px 20px rgba(0,0,0,0.18)',
            overflow: 'hidden',
            flexShrink: 0,
          }}
        >
          {/* 여백 가이드 라인 */}
          <div
            data-canvas-bg="true"
            style={{
              position: 'absolute',
              left:   px(pageSettings.margins.left),
              top:    px(pageSettings.margins.top),
              width:  px(pageW - pageSettings.margins.left - pageSettings.margins.right),
              height: px(pageH - pageSettings.margins.top  - pageSettings.margins.bottom),
              border: '1px dashed #b0b8d0',
              pointerEvents: 'none',
              zIndex: 1,
            }}
          />

          {/* 요소들 */}
          {sortedElements.map((el) => {
            const isSelected = selectedIds.includes(el.id);
            return (
              <React.Fragment key={el.id}>
                {/* 클릭 영역 */}
                <div
                  onMouseDown={(e) => handleElementMouseDown(e, el.id)}
                  style={{
                    position:  'absolute',
                    left:      px(el.x),
                    top:       px(el.y),
                    width:     px(el.width),
                    height:    px(el.height),
                    zIndex:    el.zIndex + 1000,
                    cursor:    el.locked ? 'default' : 'move',
                    boxSizing: 'border-box',
                  }}
                />
                {/* 렌더링 */}
                <RenderElement el={el} scale={scale} />
                {/* 선택 핸들 */}
                {isSelected && (
                  <SelectionHandles
                    el={el}
                    scale={scale}
                    onResize={(handle, e) => handleResizeStart(handle, e, el.id)}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* 용지 크기 표시 */}
        <div className="text-center mt-2 text-xs text-gray-400">
          {pageSettings.size} {pageSettings.orientation === 'portrait' ? '세로' : '가로'} —
          {pageW}×{pageH}mm — {Math.round(zoom * 100)}%
        </div>
      </div>
    </div>
  );
}
