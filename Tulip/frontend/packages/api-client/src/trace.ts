/**
 * W3C Trace Context (traceparent) 생성 유틸
 */

function randomHex(length: number): string {
  const bytes = new Uint8Array(length / 2);
  if (typeof globalThis.crypto !== 'undefined' && globalThis.crypto.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < bytes.length; i += 1) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * W3C traceparent 헤더 값 생성
 * 형식: `00-<trace-id 32>-<parent-id 16>-01`
 */
export function generateTraceparent(): string {
  return `00-${randomHex(32)}-${randomHex(16)}-01`;
}

/** UUIDv4 fallback (멱등성 키 등) */
export function generateUuid(): string {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  // RFC4122 v4 fallback
  const hex = randomHex(32).split('');
  hex[12] = '4';
  const yPos = 16;
  const yVal = parseInt(hex[yPos] ?? '0', 16);
  hex[yPos] = ((yVal & 0x3) | 0x8).toString(16);
  return `${hex.slice(0, 8).join('')}-${hex.slice(8, 12).join('')}-${hex
    .slice(12, 16)
    .join('')}-${hex.slice(16, 20).join('')}-${hex.slice(20, 32).join('')}`;
}
