'use client';

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { ReportElement, ReportTemplate, PageSettings } from '@/lib/types';
import { DEFAULT_PAGE_SETTINGS } from '@/lib/types';

interface HistoryEntry {
  elements: ReportElement[];
  pageSettings: PageSettings;
}

interface ReportStore {
  // 현재 리포트 템플릿
  template: ReportTemplate;
  // 선택된 요소 ID 목록
  selectedIds: string[];
  // 줌 레벨 (1.0 = 100%)
  zoom: number;
  // 히스토리 (undo/redo)
  past: HistoryEntry[];
  future: HistoryEntry[];
  // 눈금자 표시
  showRuler: boolean;
  // 격자 표시
  showGrid: boolean;
  // 격자 크기 (mm)
  gridSize: number;
  // 격자 스냅
  snapToGrid: boolean;

  // 액션
  setTemplate: (template: ReportTemplate) => void;
  updatePageSettings: (settings: Partial<PageSettings>) => void;
  addElement: (element: ReportElement) => void;
  updateElement: (id: string, changes: Partial<ReportElement>) => void;
  removeElements: (ids: string[]) => void;
  duplicateElements: (ids: string[]) => void;
  selectElement: (id: string, multi?: boolean) => void;
  selectAll: () => void;
  clearSelection: () => void;
  moveElements: (ids: string[], dx: number, dy: number) => void;
  bringForward: (id: string) => void;
  sendBackward: (id: string) => void;
  bringToFront: (id: string) => void;
  sendToBack: (id: string) => void;
  setZoom: (zoom: number) => void;
  undo: () => void;
  redo: () => void;
  toggleRuler: () => void;
  toggleGrid: () => void;
  toggleSnapToGrid: () => void;
  setGridSize: (size: number) => void;
  saveSnapshot: () => void;
}

const DEFAULT_TEMPLATE: ReportTemplate = {
  id: 'default',
  name: '새 리포트',
  pageSettings: DEFAULT_PAGE_SETTINGS,
  elements: [],
};

export const useReportStore = create<ReportStore>()(
  immer((set, get) => ({
    template: DEFAULT_TEMPLATE,
    selectedIds: [],
    zoom: 1,
    past: [],
    future: [],
    showRuler: true,
    showGrid: false,
    gridSize: 5,
    snapToGrid: false,

    setTemplate: (template) => set((s) => { s.template = template; }),

    updatePageSettings: (settings) =>
      set((s) => {
        Object.assign(s.template.pageSettings, settings);
        if (settings.margins) {
          Object.assign(s.template.pageSettings.margins, settings.margins);
        }
      }),

    addElement: (element) =>
      set((s) => {
        get().saveSnapshot();
        s.template.elements.push(element);
        s.selectedIds = [element.id];
      }),

    updateElement: (id, changes) =>
      set((s) => {
        const el = s.template.elements.find((e) => e.id === id);
        if (el) Object.assign(el, changes);
      }),

    removeElements: (ids) =>
      set((s) => {
        get().saveSnapshot();
        s.template.elements = s.template.elements.filter(
          (e) => !ids.includes(e.id),
        );
        s.selectedIds = s.selectedIds.filter((id) => !ids.includes(id));
      }),

    duplicateElements: (ids) =>
      set((s) => {
        get().saveSnapshot();
        const newEls: ReportElement[] = [];
        ids.forEach((id) => {
          const el = s.template.elements.find((e) => e.id === id);
          if (!el) return;
          const copy = {
            ...el,
            id: `el-${Date.now()}-${Math.random().toString(36).slice(2)}`,
            x: el.x + 5,
            y: el.y + 5,
            name: el.name + ' (복사)',
            zIndex: el.zIndex + 100,
          } as ReportElement;
          newEls.push(copy);
        });
        s.template.elements.push(...newEls);
        s.selectedIds = newEls.map((e) => e.id);
      }),

    selectElement: (id, multi = false) =>
      set((s) => {
        if (multi) {
          if (s.selectedIds.includes(id)) {
            s.selectedIds = s.selectedIds.filter((i) => i !== id);
          } else {
            s.selectedIds.push(id);
          }
        } else {
          s.selectedIds = [id];
        }
      }),

    selectAll: () =>
      set((s) => {
        s.selectedIds = s.template.elements.map((e) => e.id);
      }),

    clearSelection: () => set((s) => { s.selectedIds = []; }),

    moveElements: (ids, dx, dy) =>
      set((s) => {
        ids.forEach((id) => {
          const el = s.template.elements.find((e) => e.id === id);
          if (el && !el.locked) {
            el.x += dx;
            el.y += dy;
          }
        });
      }),

    bringForward: (id) =>
      set((s) => {
        const el = s.template.elements.find((e) => e.id === id);
        if (el) el.zIndex += 1;
      }),

    sendBackward: (id) =>
      set((s) => {
        const el = s.template.elements.find((e) => e.id === id);
        if (el && el.zIndex > 0) el.zIndex -= 1;
      }),

    bringToFront: (id) =>
      set((s) => {
        const max = Math.max(0, ...s.template.elements.map((e) => e.zIndex));
        const el = s.template.elements.find((e) => e.id === id);
        if (el) el.zIndex = max + 1;
      }),

    sendToBack: (id) =>
      set((s) => {
        const el = s.template.elements.find((e) => e.id === id);
        if (el) el.zIndex = 0;
      }),

    setZoom: (zoom) => set((s) => { s.zoom = Math.min(3, Math.max(0.25, zoom)); }),

    saveSnapshot: () => {
      const { template, past } = get();
      const entry: HistoryEntry = {
        elements: JSON.parse(JSON.stringify(template.elements)),
        pageSettings: JSON.parse(JSON.stringify(template.pageSettings)),
      };
      set((s) => {
        s.past = [...past.slice(-49), entry];
        s.future = [];
      });
    },

    undo: () =>
      set((s) => {
        if (s.past.length === 0) return;
        const prev = s.past[s.past.length - 1];
        s.future.unshift({
          elements: JSON.parse(JSON.stringify(s.template.elements)),
          pageSettings: JSON.parse(JSON.stringify(s.template.pageSettings)),
        });
        s.template.elements = prev.elements;
        s.template.pageSettings = prev.pageSettings;
        s.past = s.past.slice(0, -1);
      }),

    redo: () =>
      set((s) => {
        if (s.future.length === 0) return;
        const next = s.future[0];
        s.past.push({
          elements: JSON.parse(JSON.stringify(s.template.elements)),
          pageSettings: JSON.parse(JSON.stringify(s.template.pageSettings)),
        });
        s.template.elements = next.elements;
        s.template.pageSettings = next.pageSettings;
        s.future = s.future.slice(1);
      }),

    toggleRuler: () => set((s) => { s.showRuler = !s.showRuler; }),
    toggleGrid: () => set((s) => { s.showGrid = !s.showGrid; }),
    toggleSnapToGrid: () => set((s) => { s.snapToGrid = !s.snapToGrid; }),
    setGridSize: (size) => set((s) => { s.gridSize = size; }),
  })),
);
