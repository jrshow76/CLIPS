/**
 * PKCE (RFC 7636) 유틸
 *
 * - code_verifier: 43~128자 random
 * - code_challenge = BASE64URL(SHA-256(code_verifier))
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

export function generateCodeVerifier(): string {
  return urlSafe(PKCE_VERIFIER_LENGTH);
}

export async function generateCodeChallenge(verifier: string): Promise<string> {
  if (typeof globalThis.crypto?.subtle === 'undefined') {
    // SSR 환경 등 SubtleCrypto 부재 시 plain 챌린지(권장X). 클라이언트 사용 전제.
    return verifier;
  }
  const encoded = new TextEncoder().encode(verifier);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', encoded);
  return base64UrlEncode(digest);
}

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
