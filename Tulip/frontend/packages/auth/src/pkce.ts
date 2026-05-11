/**
 * PKCE (RFC 7636) 유틸 — **Deprecated (Phase 1-B)**
 *
 * Phase 1-B에서 BFF 패턴으로 전환되어 PKCE state/verifier는
 * iam-service가 보관·검증한다. 본 모듈은 호환성을 위해 유지하되
 * `@tulip/auth`의 기본 export에서 제외된다 (`index.ts` 참조).
 *
 * 신규 코드에서는 사용하지 말 것. `AuthClient.initiateLogin`를 사용한다.
 */
import type { PkceChallenge } from './types';

const PKCE_VERIFIER_LENGTH = 64;

function randomBytes(length: number): Uint8Array {
  const arr = new Uint8Array(length);
  if (typeof globalThis.crypto !== 'undefined' && globalThis.crypto.getRandomValues) {
    globalThis.crypto.getRandomValues(arr);
  } else {
    for (let i = 0; i < length; i += 1) arr[i] = Math.floor(Math.random() * 256);
  }
  return arr;
}

function base64UrlEncode(bytes: Uint8Array | ArrayBuffer): string {
  const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let str = '';
  for (let i = 0; i < u8.length; i += 1) str += String.fromCharCode(u8[i] ?? 0);
  return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function urlSafe(length: number): string {
  return base64UrlEncode(randomBytes(length)).slice(0, length);
}

/** @deprecated Phase 1-B에서는 iam-service가 verifier를 보관한다. */
export function generateCodeVerifier(): string {
  return urlSafe(PKCE_VERIFIER_LENGTH);
}

/** @deprecated */
export async function generateCodeChallenge(verifier: string): Promise<string> {
  if (typeof globalThis.crypto?.subtle === 'undefined') {
    return verifier;
  }
  const encoded = new TextEncoder().encode(verifier);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', encoded);
  return base64UrlEncode(digest);
}

/** @deprecated */
export async function generatePkceChallenge(): Promise<PkceChallenge> {
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);
  return {
    codeVerifier,
    codeChallenge,
    state: urlSafe(32),
    nonce: urlSafe(32),
  };
}
