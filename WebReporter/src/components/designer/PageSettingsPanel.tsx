'use client';

import React, { useState } from 'react';
import { Settings, ChevronDown, ChevronRight } from 'lucide-react';
import { useReportStore } from '@/store/useReportStore';
import { PAPER_SIZES } from '@/lib/paper-sizes';
import type { PaperSize, Orientation } from '@/lib/types';

export default function PageSettingsPanel() {
  const { template, updatePageSettings } = useReportStore();
  const { pageSettings } = template;
  const [open, setOpen] = useState(true);

  const upd = (changes: Parameters<typeof updatePageSettings>[0]) =>
    updatePageSettings(changes);

  return (
    <div className="border-b border-gray-200 bg-panel-bg flex-shrink-0">
      <button
        className="flex items-center gap-2 w-full px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <Settings size={13} />
        페이지 설정
        {open ? <ChevronDown size={13} className="ml-auto" /> : <ChevronRight size={13} className="ml-auto" />}
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-3">
          {/* 용지 크기 */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">용지 크기</label>
            <select
              className="w-full bg-white border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-accent"
              value={pageSettings.size}
              onChange={(e) => upd({ size: e.target.value as PaperSize })}
            >
              {(Object.keys(PAPER_SIZES) as PaperSize[]).map((k) => (
                <option key={k} value={k}>{PAPER_SIZES[k].label}</option>
              ))}
            </select>
          </div>

          {/* 방향 */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">방향</label>
            <div className="flex gap-2">
              {(['portrait', 'landscape'] as Orientation[]).map((o) => (
                <button
                  key={o}
                  onClick={() => upd({ orientation: o })}
                  className={`flex-1 py-1 text-xs rounded border transition-colors ${
                    pageSettings.orientation === o
                      ? 'bg-accent text-white border-accent'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-accent'
                  }`}
                >
                  {o === 'portrait' ? '⬜ 세로' : '⬛ 가로'}
                </button>
              ))}
            </div>
          </div>

          {/* 여백 */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">여백 (mm)</label>
            <div className="grid grid-cols-2 gap-1.5">
              {(['top', 'bottom', 'left', 'right'] as const).map((side) => {
                const labels = { top: '위', bottom: '아래', left: '왼쪽', right: '오른쪽' };
                return (
                  <div key={side} className="flex flex-col">
                    <span className="text-xs text-gray-400">{labels[side]}</span>
                    <input
                      type="number"
                      className="bg-white border border-gray-200 rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-accent"
                      value={pageSettings.margins[side]}
                      min={0}
                      max={50}
                      step={1}
                      onChange={(e) =>
                        upd({
                          margins: {
                            ...pageSettings.margins,
                            [side]: parseFloat(e.target.value) || 0,
                          },
                        })
                      }
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
