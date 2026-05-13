'use client';

import { useRealtimeStatus } from '@/hooks/useRealtimeStatus';

/**
 * 헤더 등 상시 노출용 실시간 연결 상태 점등 인디케이터.
 *
 * - 녹색: 모든 채널 OPEN (LIVE)
 * - 노랑: 1개 이상 connecting/reconnecting
 * - 빨강: 모두 closed/idle
 *
 * 단순 점 + 라벨. CSS는 인라인으로 (디자인 시스템 변수만 활용).
 */
export interface RealtimeIndicatorProps {
  /** 라벨 노출 여부 (기본 true) */
  showLabel?: boolean;
  className?: string;
}

export function RealtimeIndicator({ showLabel = true, className }: RealtimeIndicatorProps) {
  const { allOpen, anyConnecting, market, account, notifications } = useRealtimeStatus();

  let color = '#ef4444'; // red - 끊김
  let label = '연결 끊김';
  let pulse = false;
  if (allOpen) {
    color = '#22c55e'; // green - LIVE
    label = 'LIVE';
    pulse = true;
  } else if (anyConnecting) {
    color = '#facc15'; // yellow - 재연결 중
    label = '재연결 중';
  } else if (market === 'open' || account === 'open' || notifications === 'open') {
    color = '#facc15';
    label = '부분 연결';
  }

  return (
    <span
      className={className}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}
      title={`market=${market} / account=${account} / notifications=${notifications}`}
      aria-live="polite"
    >
      <span
        aria-hidden="true"
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: color,
          boxShadow: pulse ? `0 0 0 0 ${color}99` : undefined,
          animation: pulse ? 'tp-realtime-pulse 1.6s ease-out infinite' : undefined,
        }}
      />
      {showLabel && <span style={{ color: 'var(--color-text-subtle, #94a3b8)' }}>{label}</span>}
      <style jsx>{`
        @keyframes tp-realtime-pulse {
          0% {
            box-shadow: 0 0 0 0 ${color}66;
          }
          70% {
            box-shadow: 0 0 0 6px ${color}00;
          }
          100% {
            box-shadow: 0 0 0 0 ${color}00;
          }
        }
      `}</style>
    </span>
  );
}
