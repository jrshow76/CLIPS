/**
 * className 유틸 (clsx + tailwind-merge)
 * 컴포넌트 내부에서 클래스 병합·중복 정리에 사용.
 */
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
