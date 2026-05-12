'use client';

import {
  ColorType,
  CrosshairMode,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from 'lightweight-charts';
import { useEffect, useRef } from 'react';

import type { Candle } from '@/types/stock';

export interface CandlestickChartProps {
  data: Candle[];
  /** 거래량 패널 노출 */
  withVolume?: boolean;
  /** 이동평균 (예: [5, 20, 60]) */
  movingAverages?: number[];
  height?: number;
  /** 다크/라이트 색상 */
  theme?: 'dark' | 'light';
}

/**
 * lightweight-charts 기반 캔들 차트 래퍼.
 * - 상승 = 빨강(#ef4444), 하락 = 파랑(#3b82f6) - 국내 컨벤션
 * - withVolume: 하단 거래량 히스토그램
 * - movingAverages: 종가 기준 SMA 라인 오버레이
 *
 * Note: lightweight-charts는 클라이언트 전용. dynamic import로 SSR 제외.
 */
export function CandlestickChart({
  data,
  withVolume = true,
  movingAverages = [5, 20, 60],
  height = 420,
  theme = 'dark',
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const bg = theme === 'dark' ? '#161c27' : '#ffffff';
    const text = theme === 'dark' ? '#b6c0cf' : '#475569';
    const grid = theme === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(15,23,42,0.06)';

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: { background: { type: ColorType.Solid, color: bg }, textColor: text },
      grid: { vertLines: { color: grid }, horzLines: { color: grid } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true },
      crosshair: { mode: CrosshairMode.Magnet },
    });
    chartRef.current = chart;

    const candleSeries: ISeriesApi<'Candlestick'> = chart.addCandlestickSeries({
      upColor: '#ef4444',
      downColor: '#3b82f6',
      borderUpColor: '#ef4444',
      borderDownColor: '#3b82f6',
      wickUpColor: '#ef4444',
      wickDownColor: '#3b82f6',
    });

    candleSeries.setData(
      data.map((c) => ({
        time: Math.floor(c.ts / 1000) as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    );

    // 이동평균 라인
    const palette = ['#facc15', '#22d3ee', '#a78bfa', '#34d399'];
    movingAverages.forEach((period, idx) => {
      const ma = chart.addLineSeries({
        color: palette[idx % palette.length],
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      ma.setData(calcSMA(data, period));
    });

    // 거래량
    if (withVolume) {
      const volume = chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      });
      volume.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
      volume.setData(
        data.map((c) => ({
          time: Math.floor(c.ts / 1000) as Time,
          value: c.volume,
          color: c.close >= c.open ? 'rgba(239,68,68,0.5)' : 'rgba(59,130,246,0.5)',
        })),
      );
    }

    const onResize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener('resize', onResize);

    return () => {
      window.removeEventListener('resize', onResize);
      chart.remove();
    };
  }, [data, withVolume, movingAverages, height, theme]);

  return <div ref={containerRef} style={{ width: '100%', height }} />;
}

function calcSMA(data: Candle[], period: number): { time: Time; value: number }[] {
  const out: { time: Time; value: number }[] = [];
  for (let i = period - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = 0; j < period; j++) sum += data[i - j]?.close ?? 0;
    const item = data[i];
    if (!item) continue;
    out.push({ time: Math.floor(item.ts / 1000) as Time, value: sum / period });
  }
  return out;
}
