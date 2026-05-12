import { format } from 'date-fns';
import { toZonedTime } from 'date-fns-tz';

const KST_TZ = 'Asia/Seoul';

/**
 * 한국시간(KST) 기준 포맷터.
 * 서버 응답이 ISO+오프셋 또는 epoch ms 두 가지 모두 들어오므로 자동 처리.
 */
export function formatKST(input: string | number | Date, pattern = 'yyyy-MM-dd HH:mm:ss'): string {
  const d = typeof input === 'string' || typeof input === 'number' ? new Date(input) : input;
  if (Number.isNaN(d.getTime())) return '-';
  const zoned = toZonedTime(d, KST_TZ);
  return format(zoned, pattern);
}

export function formatKSTDate(input: string | number | Date): string {
  return formatKST(input, 'yyyy-MM-dd');
}

export function formatKSTTime(input: string | number | Date): string {
  return formatKST(input, 'HH:mm:ss');
}

/** 상대시간 (n분 전 / n시간 전) — 간단 구현 */
export function formatRelativeKR(input: string | number | Date): string {
  const target = new Date(input).getTime();
  if (Number.isNaN(target)) return '-';
  const diffSec = Math.round((Date.now() - target) / 1000);
  if (diffSec < 60) return `${Math.max(diffSec, 0)}초 전`;
  const min = Math.round(diffSec / 60);
  if (min < 60) return `${min}분 전`;
  const hour = Math.round(min / 60);
  if (hour < 24) return `${hour}시간 전`;
  const day = Math.round(hour / 24);
  if (day < 30) return `${day}일 전`;
  return formatKSTDate(input);
}

export const KST_TIMEZONE = KST_TZ;
