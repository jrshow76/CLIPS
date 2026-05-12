import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Tailwind 클래스 결합 유틸.
 * - clsx로 truthy 처리 + twMerge로 충돌 해결.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
