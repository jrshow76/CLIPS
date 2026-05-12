'use client';

import { useMemo } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { Candle } from '@/types/stock';

export type IndicatorKind = 'RSI' | 'MACD' | 'STOCH';

export interface IndicatorPanelProps {
  kind: IndicatorKind;
  candles: Candle[];
  height?: number;
}

/**
 * RSI / MACD / Stochastic 보조 패널.
 * - 메인 캔들과 별개의 영역에 표시.
 * - 간단한 계산을 클라이언트에서 수행 (정확도 우선이면 백엔드 /indicators API로 대체).
 */
export function IndicatorPanel({ kind, candles, height = 140 }: IndicatorPanelProps) {
  const data = useMemo(() => calcIndicator(kind, candles), [kind, candles]);

  return (
    <div className="border-border-1 bg-bg-2 rounded-md border p-2" style={{ height }}>
      <div className="text-subtle px-2 pb-1 text-xs">{kind}</div>
      <ResponsiveContainer width="100%" height={height - 28}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--chart-grid-1)" />
          <XAxis dataKey="t" hide />
          <YAxis
            domain={kind === 'RSI' || kind === 'STOCH' ? [0, 100] : ['auto', 'auto']}
            width={28}
            tick={{ fill: 'var(--color-text-3)', fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--color-bg-2)',
              border: '1px solid var(--color-border-2)',
              fontSize: 12,
            }}
            labelFormatter={() => ''}
          />
          {kind === 'RSI' && <ReferenceLine y={70} stroke="var(--color-up)" strokeDasharray="2 4" />}
          {kind === 'RSI' && <ReferenceLine y={30} stroke="var(--color-down)" strokeDasharray="2 4" />}
          <Line type="monotone" dataKey="v" stroke="var(--color-brand-500)" dot={false} strokeWidth={1.4} />
          {kind === 'MACD' && (
            <Line type="monotone" dataKey="signal" stroke="var(--color-warning)" dot={false} strokeWidth={1.2} />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ============================================================
 *  지표 계산 (간이 구현 - 데모용)
 * ============================================================ */
function calcIndicator(kind: IndicatorKind, candles: Candle[]) {
  if (kind === 'RSI') return calcRSI(candles, 14);
  if (kind === 'MACD') return calcMACD(candles, 12, 26, 9);
  return calcStoch(candles, 14);
}

function calcRSI(candles: Candle[], period: number) {
  const out: { t: number; v: number }[] = [];
  let gains = 0;
  let losses = 0;
  for (let i = 1; i < candles.length; i++) {
    const prev = candles[i - 1]!;
    const cur = candles[i]!;
    const diff = cur.close - prev.close;
    const gain = Math.max(diff, 0);
    const loss = Math.max(-diff, 0);
    if (i <= period) {
      gains += gain;
      losses += loss;
      if (i === period) {
        const rs = losses === 0 ? 100 : gains / losses;
        out.push({ t: cur.ts, v: 100 - 100 / (1 + rs) });
      }
    } else {
      gains = (gains * (period - 1) + gain) / period;
      losses = (losses * (period - 1) + loss) / period;
      const rs = losses === 0 ? 100 : gains / losses;
      out.push({ t: cur.ts, v: 100 - 100 / (1 + rs) });
    }
  }
  return out;
}

function ema(values: number[], period: number) {
  const k = 2 / (period + 1);
  const out: number[] = [];
  values.forEach((v, i) => {
    out[i] = i === 0 ? v : v * k + (out[i - 1] ?? v) * (1 - k);
  });
  return out;
}

function calcMACD(candles: Candle[], fast: number, slow: number, signal: number) {
  const closes = candles.map((c) => c.close);
  const emaFast = ema(closes, fast);
  const emaSlow = ema(closes, slow);
  const macd = emaFast.map((v, i) => v - (emaSlow[i] ?? v));
  const sig = ema(macd, signal);
  return candles.map((c, i) => ({ t: c.ts, v: macd[i] ?? 0, signal: sig[i] ?? 0 }));
}

function calcStoch(candles: Candle[], period: number) {
  const out: { t: number; v: number }[] = [];
  for (let i = period - 1; i < candles.length; i++) {
    const win = candles.slice(i - period + 1, i + 1);
    const low = Math.min(...win.map((c) => c.low));
    const high = Math.max(...win.map((c) => c.high));
    const cur = candles[i]!;
    const k = high === low ? 50 : ((cur.close - low) / (high - low)) * 100;
    out.push({ t: cur.ts, v: k });
  }
  return out;
}
