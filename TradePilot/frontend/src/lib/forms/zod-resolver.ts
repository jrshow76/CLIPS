import type { FieldErrors, FieldValues, Resolver } from 'react-hook-form';
import type { ZodTypeAny, ZodError } from 'zod';

/**
 * @hookform/resolvers 를 추가 설치하지 않고 사용하기 위한 자체 zod resolver.
 * - 동작: schema.safeParse(values) → 성공 시 parsed 데이터, 실패 시 RHF 호환 errors.
 * - 중첩 경로(array index 포함)는 issue.path로 그대로 매핑한다.
 */
export function zodResolver<TIn extends FieldValues, TOut extends FieldValues = TIn>(
  schema: ZodTypeAny,
): Resolver<TIn, unknown, TOut> {
  return async (values) => {
    const result = schema.safeParse(values);
    if (result.success) {
      return { values: result.data as TOut, errors: {} };
    }
    return { values: {} as TOut, errors: toRhfErrors<TIn>(result.error) };
  };
}

function toRhfErrors<T extends FieldValues>(zerr: ZodError): FieldErrors<T> {
  const errors: Record<string, unknown> = {};
  for (const issue of zerr.issues) {
    if (issue.path.length === 0) {
      // 폼 전체 에러는 RHF의 root 영역에 매핑
      const root = (errors.root as Record<string, unknown> | undefined) ?? {};
      root[issue.code] = { type: issue.code, message: issue.message };
      errors.root = root;
      continue;
    }
    setDeep(errors, issue.path as (string | number)[], {
      type: issue.code,
      message: issue.message,
    });
  }
  return errors as FieldErrors<T>;
}

function setDeep(target: Record<string, unknown>, path: (string | number)[], value: unknown) {
  let cur: Record<string, unknown> = target;
  for (let i = 0; i < path.length - 1; i++) {
    const key = String(path[i]);
    const next = cur[key];
    if (typeof next !== 'object' || next === null) {
      cur[key] = {};
    }
    cur = cur[key] as Record<string, unknown>;
  }
  cur[String(path[path.length - 1])] = value;
}
