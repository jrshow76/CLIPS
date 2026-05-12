'use client';

import React from 'react';
import { useReportStore } from '@/store/useReportStore';
import type {
  ReportElement, TextElement, RectElement,
  LineElement, ImageElement, EllipseElement,
} from '@/lib/types';

// ─── 공통 입력 컴포넌트 ─────────────────────────────────────────────────────

function Label({ children }: { children: React.ReactNode }) {
  return <span className="text-xs text-gray-400 mb-0.5">{children}</span>;
}

function NumberInput({
  label, value, onChange, min, max, step = 0.5, unit = 'mm',
}: {
  label: string; value: number; onChange: (v: number) => void;
  min?: number; max?: number; step?: number; unit?: string;
}) {
  return (
    <div className="flex flex-col">
      <Label>{label}</Label>
      <div className="flex items-center">
        <input
          type="number"
          className="w-full bg-white border border-gray-200 rounded px-1.5 py-0.5 text-xs text-gray-700 focus:outline-none focus:ring-1 focus:ring-accent"
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        />
        {unit && <span className="ml-1 text-xs text-gray-400 w-5">{unit}</span>}
      </div>
    </div>
  );
}

function TextInput({
  label, value, onChange,
}: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col">
      <Label>{label}</Label>
      <input
        type="text"
        className="w-full bg-white border border-gray-200 rounded px-1.5 py-0.5 text-xs text-gray-700 focus:outline-none focus:ring-1 focus:ring-accent"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function ColorInput({
  label, value, onChange,
}: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col">
      <Label>{label}</Label>
      <div className="flex items-center gap-1">
        <input
          type="color"
          className="w-7 h-7 rounded border border-gray-200 cursor-pointer p-0"
          value={value === 'transparent' ? '#ffffff' : value}
          onChange={(e) => onChange(e.target.value)}
        />
        <input
          type="text"
          className="flex-1 bg-white border border-gray-200 rounded px-1.5 py-0.5 text-xs text-gray-700 focus:outline-none"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    </div>
  );
}

function SelectInput<T extends string>({
  label, value, options, onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex flex-col">
      <Label>{label}</Label>
      <select
        className="w-full bg-white border border-gray-200 rounded px-1.5 py-1 text-xs text-gray-700 focus:outline-none"
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-gray-100 pb-3 mb-3">
      <div className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">{title}</div>
      <div className="grid grid-cols-2 gap-x-2 gap-y-2">{children}</div>
    </div>
  );
}

// ─── 속성 패널 본체 ─────────────────────────────────────────────────────────

export default function PropertyPanel() {
  const { template, selectedIds, updateElement } = useReportStore();
  const { elements } = template;

  if (selectedIds.length === 0) {
    return (
      <div className="w-64 flex-shrink-0 bg-panel-bg border-l border-gray-200 p-4 text-xs text-gray-400 flex items-center justify-center">
        요소를 선택하면 속성을 편집할 수 있습니다.
      </div>
    );
  }

  if (selectedIds.length > 1) {
    return (
      <div className="w-64 flex-shrink-0 bg-panel-bg border-l border-gray-200 p-4 text-xs text-gray-400 flex items-center justify-center">
        {selectedIds.length}개 요소 선택됨
      </div>
    );
  }

  const el = elements.find((e) => e.id === selectedIds[0]);
  if (!el) return null;

  const upd = (changes: Partial<ReportElement>) => updateElement(el.id, changes);

  return (
    <div className="w-64 flex-shrink-0 bg-panel-bg border-l border-gray-200 overflow-y-auto">
      <div className="px-3 py-2 bg-white border-b border-gray-200">
        <div className="text-xs font-bold text-gray-600">속성 패널</div>
        <div className="text-xs text-gray-400">{el.name} ({el.type})</div>
      </div>
      <div className="p-3">
        {/* 공통 위치/크기 */}
        <Section title="위치 · 크기">
          <NumberInput label="X" value={el.x} onChange={(v) => upd({ x: v })} />
          <NumberInput label="Y" value={el.y} onChange={(v) => upd({ y: v })} />
          <NumberInput label="너비" value={el.width}  onChange={(v) => upd({ width:  Math.max(1, v) })} min={1} />
          <NumberInput label="높이" value={el.height} onChange={(v) => upd({ height: Math.max(1, v) })} min={1} />
        </Section>

        {/* 이름 */}
        <div className="border-b border-gray-100 pb-3 mb-3">
          <TextInput
            label="요소 이름"
            value={el.name}
            onChange={(v) => upd({ name: v })}
          />
        </div>

        {/* 텍스트 속성 */}
        {el.type === 'text' && <TextProperties el={el as TextElement} upd={upd} />}
        {el.type === 'rect' && <RectProperties el={el as RectElement} upd={upd} />}
        {el.type === 'line' && <LineProperties el={el as LineElement} upd={upd} />}
        {el.type === 'image' && <ImageProperties el={el as ImageElement} upd={upd} />}
        {el.type === 'ellipse' && <EllipseProperties el={el as EllipseElement} upd={upd} />}
      </div>
    </div>
  );
}

// ─── 요소별 속성 ─────────────────────────────────────────────────────────────

function TextProperties({ el, upd }: { el: TextElement; upd: (c: Partial<ReportElement>) => void }) {
  return (
    <>
      <Section title="텍스트 내용">
        <div className="col-span-2 flex flex-col">
          <Label>내용</Label>
          <textarea
            className="w-full bg-white border border-gray-200 rounded px-1.5 py-1 text-xs text-gray-700 focus:outline-none focus:ring-1 focus:ring-accent resize-none"
            rows={3}
            value={el.content}
            onChange={(e) => upd({ content: e.target.value })}
          />
        </div>
      </Section>

      <Section title="폰트">
        <NumberInput label="크기" value={el.fontSize} onChange={(v) => upd({ fontSize: v })} min={4} max={200} step={1} unit="pt" />
        <SelectInput
          label="정렬"
          value={el.textAlign}
          options={[
            { value: 'left',    label: '왼쪽' },
            { value: 'center',  label: '가운데' },
            { value: 'right',   label: '오른쪽' },
            { value: 'justify', label: '양쪽' },
          ]}
          onChange={(v) => upd({ textAlign: v })}
        />
        <SelectInput
          label="굵기"
          value={el.fontWeight}
          options={[{ value: 'normal', label: '보통' }, { value: 'bold', label: '굵게' }]}
          onChange={(v) => upd({ fontWeight: v })}
        />
        <SelectInput
          label="기울기"
          value={el.fontStyle}
          options={[{ value: 'normal', label: '보통' }, { value: 'italic', label: '기울기' }]}
          onChange={(v) => upd({ fontStyle: v })}
        />
        <NumberInput label="줄 높이" value={el.lineHeight} onChange={(v) => upd({ lineHeight: v })} min={0.8} max={4} step={0.1} unit="x" />
      </Section>

      <Section title="색상">
        <div className="col-span-2">
          <ColorInput label="글자색" value={el.color} onChange={(v) => upd({ color: v })} />
        </div>
        <div className="col-span-2">
          <ColorInput label="배경색" value={el.backgroundColor} onChange={(v) => upd({ backgroundColor: v })} />
        </div>
        <div className="col-span-2">
          <ColorInput label="테두리색" value={el.borderColor} onChange={(v) => upd({ borderColor: v })} />
        </div>
        <NumberInput label="테두리 두께" value={el.borderWidth} onChange={(v) => upd({ borderWidth: v })} min={0} step={0.5} unit="px" />
      </Section>

      <Section title="패딩">
        <NumberInput label="위"    value={el.paddingTop}    onChange={(v) => upd({ paddingTop: v })}    min={0} />
        <NumberInput label="아래"  value={el.paddingBottom} onChange={(v) => upd({ paddingBottom: v })} min={0} />
        <NumberInput label="왼쪽" value={el.paddingLeft}   onChange={(v) => upd({ paddingLeft: v })}   min={0} />
        <NumberInput label="오른쪽" value={el.paddingRight}  onChange={(v) => upd({ paddingRight: v })}  min={0} />
      </Section>
    </>
  );
}

function RectProperties({ el, upd }: { el: RectElement; upd: (c: Partial<ReportElement>) => void }) {
  return (
    <Section title="사각형 스타일">
      <div className="col-span-2">
        <ColorInput label="채우기" value={el.fillColor} onChange={(v) => upd({ fillColor: v })} />
      </div>
      <div className="col-span-2">
        <ColorInput label="테두리" value={el.strokeColor} onChange={(v) => upd({ strokeColor: v })} />
      </div>
      <NumberInput label="테두리 두께" value={el.strokeWidth}  onChange={(v) => upd({ strokeWidth: v })}  min={0} step={0.5} unit="px" />
      <NumberInput label="모서리 반경" value={el.borderRadius} onChange={(v) => upd({ borderRadius: v })} min={0} step={1}   unit="px" />
      <NumberInput label="투명도" value={el.opacity} onChange={(v) => upd({ opacity: Math.min(1, Math.max(0, v)) })} min={0} max={1} step={0.1} unit="" />
    </Section>
  );
}

function LineProperties({ el, upd }: { el: LineElement; upd: (c: Partial<ReportElement>) => void }) {
  return (
    <Section title="라인 스타일">
      <div className="col-span-2">
        <ColorInput label="색상" value={el.color} onChange={(v) => upd({ color: v })} />
      </div>
      <NumberInput label="두께" value={el.strokeWidth} onChange={(v) => upd({ strokeWidth: v })} min={0.5} step={0.5} unit="px" />
      <SelectInput
        label="방향"
        value={el.direction}
        options={[
          { value: 'horizontal',    label: '가로' },
          { value: 'vertical',      label: '세로' },
          { value: 'diagonal-down', label: '대각선(↘)' },
          { value: 'diagonal-up',   label: '대각선(↗)' },
        ]}
        onChange={(v) => upd({ direction: v })}
      />
      <div className="col-span-2 flex items-center gap-2">
        <input
          type="checkbox"
          id="dashed"
          checked={el.dashed}
          onChange={(e) => upd({ dashed: e.target.checked })}
        />
        <label htmlFor="dashed" className="text-xs text-gray-600">점선</label>
      </div>
    </Section>
  );
}

function ImageProperties({ el, upd }: { el: ImageElement; upd: (c: Partial<ReportElement>) => void }) {
  return (
    <Section title="이미지">
      <div className="col-span-2">
        <TextInput label="이미지 URL" value={el.src} onChange={(v) => upd({ src: v })} />
      </div>
      <SelectInput
        label="맞춤"
        value={el.objectFit}
        options={[
          { value: 'contain', label: '맞춤 (contain)' },
          { value: 'cover',   label: '채우기 (cover)' },
          { value: 'fill',    label: '늘이기 (fill)' },
          { value: 'none',    label: '원본 (none)' },
        ]}
        onChange={(v) => upd({ objectFit: v })}
      />
      <NumberInput label="투명도" value={el.opacity} onChange={(v) => upd({ opacity: Math.min(1, Math.max(0, v)) })} min={0} max={1} step={0.1} unit="" />
    </Section>
  );
}

function EllipseProperties({ el, upd }: { el: EllipseElement; upd: (c: Partial<ReportElement>) => void }) {
  return (
    <Section title="타원 스타일">
      <div className="col-span-2">
        <ColorInput label="채우기" value={el.fillColor} onChange={(v) => upd({ fillColor: v })} />
      </div>
      <div className="col-span-2">
        <ColorInput label="테두리" value={el.strokeColor} onChange={(v) => upd({ strokeColor: v })} />
      </div>
      <NumberInput label="테두리 두께" value={el.strokeWidth} onChange={(v) => upd({ strokeWidth: v })} min={0} step={0.5} unit="px" />
      <NumberInput label="투명도" value={el.opacity} onChange={(v) => upd({ opacity: Math.min(1, Math.max(0, v)) })} min={0} max={1} step={0.1} unit="" />
    </Section>
  );
}
