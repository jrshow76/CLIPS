'use client';

import React, { useState } from 'react';
import { Layers, ChevronDown, ChevronRight, Eye, EyeOff, Lock, Unlock } from 'lucide-react';
import { useReportStore } from '@/store/useReportStore';

export default function LayerPanel() {
  const { template, selectedIds, selectElement, updateElement, removeElements } = useReportStore();
  const [open, setOpen] = useState(true);

  const elements = [...template.elements].sort((a, b) => b.zIndex - a.zIndex);

  return (
    <div className="border-b border-gray-200 bg-panel-bg flex-shrink-0 max-h-60 flex flex-col">
      <button
        className="flex items-center gap-2 w-full px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 transition-colors flex-shrink-0"
        onClick={() => setOpen((o) => !o)}
      >
        <Layers size={13} />
        레이어 ({elements.length})
        {open ? <ChevronDown size={13} className="ml-auto" /> : <ChevronRight size={13} className="ml-auto" />}
      </button>

      {open && (
        <div className="overflow-y-auto flex-1">
          {elements.length === 0 ? (
            <div className="px-3 py-2 text-xs text-gray-400">요소가 없습니다.</div>
          ) : (
            elements.map((el) => {
              const isSelected = selectedIds.includes(el.id);
              return (
                <div
                  key={el.id}
                  className={`flex items-center gap-1.5 px-2 py-1 cursor-pointer text-xs transition-colors ${
                    isSelected ? 'bg-accent/10 text-accent font-medium' : 'text-gray-600 hover:bg-gray-100'
                  }`}
                  onClick={() => selectElement(el.id)}
                >
                  <span className="truncate flex-1">{el.name}</span>
                  <button
                    className="p-0.5 hover:text-accent"
                    onClick={(e) => { e.stopPropagation(); updateElement(el.id, { locked: !el.locked }); }}
                    title={el.locked ? '잠금 해제' : '잠금'}
                  >
                    {el.locked ? <Lock size={10} /> : <Unlock size={10} />}
                  </button>
                  <button
                    className="p-0.5 hover:text-red-400"
                    onClick={(e) => { e.stopPropagation(); removeElements([el.id]); }}
                    title="삭제"
                  >
                    ×
                  </button>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
