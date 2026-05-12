'use client';

import { cn } from '@/lib/utils/cn';
import { formatPct } from '@/lib/utils/format';
import type { Sector } from '@/types/recommendation';

export interface SectorHeatmapProps {
  sectors: Sector[];
  onSelect?: (code: string) => void;
}

/**
 * 섹터 등락률 히트맵.
 * Designer의 .heatmap / .heatmap__cell--up-1~3 / --down-1~3 6단계 컬러스케일을 직접 사용.
 * (Recharts/D3 없이 CSS-grid + tokens 활용)
 */
export function SectorHeatmap({ sectors, onSelect }: SectorHeatmapProps) {
  return (
    <div className="heatmap" role="grid" aria-label="섹터 등락률">
      {sectors.map((s) => (
        <button
          key={s.code}
          type="button"
          onClick={() => onSelect?.(s.code)}
          className={cn(
            'heatmap__cell text-left',
            cellClass(s.change_pct),
            onSelect && 'hover:opacity-80',
          )}
        >
          <span className="fw-semibold truncate">{s.name}</span>
          <span className="text-num text-12">{formatPct(s.change_pct)}</span>
        </button>
      ))}
    </div>
  );
}

function cellClass(pct: number): string {
  if (pct >= 3) return 'heatmap__cell--up-3';
  if (pct >= 1.5) return 'heatmap__cell--up-2';
  if (pct > 0) return 'heatmap__cell--up-1';
  if (pct <= -3) return 'heatmap__cell--down-3';
  if (pct <= -1.5) return 'heatmap__cell--down-2';
  if (pct < 0) return 'heatmap__cell--down-1';
  return '';
}
