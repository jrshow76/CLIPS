import type { FieldValues, Path, UseFormSetError } from 'react-hook-form';

import { AppError, extractFieldErrors } from '@/lib/api/error';

/**
 * 서버에서 내려온 필드 검증 오류(E0003)를 react-hook-form의 setError에 매핑한다.
 * - AppError 외 객체는 무시하고 false 반환 (호출측에서 toast/ErrorCard 처리).
 *
 * 예:
 *   try { await mutation.mutateAsync(values); }
 *   catch (err) {
 *     if (!applyFieldErrors(err, form.setError)) toast.danger(...);
 *   }
 */
export function applyFieldErrors<T extends FieldValues>(
  err: unknown,
  setError: UseFormSetError<T>,
): boolean {
  if (!(err instanceof AppError)) return false;
  const fields = extractFieldErrors(err);
  if (!fields) return false;
  for (const [name, message] of Object.entries(fields)) {
    setError(name as Path<T>, { type: 'server', message });
  }
  return true;
}

/**
 * 단순 메시지를 추출. 페이지에서 ErrorCard에 그대로 사용.
 */
export function toUserMessage(err: unknown): string {
  if (err instanceof AppError) return err.userMessage;
  if (err instanceof Error) return err.message;
  return '알 수 없는 오류가 발생했습니다.';
}
