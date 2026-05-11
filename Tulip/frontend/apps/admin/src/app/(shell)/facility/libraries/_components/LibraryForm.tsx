'use client';

/**
 * LibraryForm — 도서관 등록·수정 공용 폼.
 *
 * - react-hook-form + zod 검증
 * - 부모 FormModal과 함께 사용 (form 태그는 본 컴포넌트가 렌더하지 않음)
 */
import { zodResolver } from '@hookform/resolvers/zod';
import type {
  CreateLibraryInput,
  Library,
  LibraryKind,
  UpdateLibraryInput,
} from '@tulip/api-client';
import { useLibrariesQuery } from '@tulip/api-client';
import { FormField, Input, Select } from '@tulip/ui';
import { forwardRef, useImperativeHandle, type ForwardedRef } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

const librarySchema = z.object({
  code: z
    .string()
    .min(1, '도서관 코드를 입력하세요.')
    .max(20, '코드는 20자 이내로 입력하세요.')
    .regex(/^[A-Z0-9_-]+$/i, '영문/숫자/_/-만 사용할 수 있습니다.'),
  name: z.string().min(1, '도서관 이름을 입력하세요.').max(60),
  kind: z.enum(['MAIN', 'BRANCH', 'BOOK_MOBILE', 'PARTNER']),
  parentId: z.string().optional().or(z.literal('').transform(() => undefined)),
  address: z.string().max(200).optional().or(z.literal('').transform(() => undefined)),
  phone: z
    .string()
    .max(20)
    .regex(/^[0-9-+\s]*$/, '연락처는 숫자·하이픈만 사용할 수 있습니다.')
    .optional()
    .or(z.literal('').transform(() => undefined)),
  email: z
    .string()
    .email('올바른 이메일 형식이 아닙니다.')
    .optional()
    .or(z.literal('').transform(() => undefined)),
  openHours: z.string().max(60).optional().or(z.literal('').transform(() => undefined)),
});

export type LibraryFormValues = z.infer<typeof librarySchema>;

export interface LibraryFormHandle {
  submit: () => void;
}

export interface LibraryFormProps {
  initial?: Library;
  onValid: (values: CreateLibraryInput | UpdateLibraryInput) => void;
}

const KIND_OPTIONS: { value: LibraryKind; label: string }[] = [
  { value: 'MAIN', label: '본관' },
  { value: 'BRANCH', label: '분관' },
  { value: 'BOOK_MOBILE', label: '이동도서관' },
  { value: 'PARTNER', label: '협력기관' },
];

function LibraryFormInner(
  { initial, onValid }: LibraryFormProps,
  ref: ForwardedRef<LibraryFormHandle>,
) {
  const mainsQuery = useLibrariesQuery({ kind: 'MAIN', size: 100 });

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<LibraryFormValues>({
    resolver: zodResolver(librarySchema),
    defaultValues: initial
      ? {
          code: initial.code,
          name: initial.name,
          kind: initial.kind,
          parentId: initial.parentId ?? undefined,
          address: initial.address ?? undefined,
          phone: initial.phone ?? undefined,
          email: initial.email ?? undefined,
          openHours: initial.openHours ?? undefined,
        }
      : {
          code: '',
          name: '',
          kind: 'BRANCH',
          parentId: undefined,
          address: undefined,
          phone: undefined,
          email: undefined,
          openHours: undefined,
        },
  });

  useImperativeHandle(ref, () => ({
    submit: () => {
      void handleSubmit((values) =>
        onValid(values as CreateLibraryInput | UpdateLibraryInput),
      )();
    },
  }));

  const kind = watch('kind');
  const parentOptions = [
    { value: '', label: '없음 (독립)' },
    ...(mainsQuery.data?.items ?? []).map((l) => ({ value: l.id, label: l.name })),
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="도서관 코드" required error={errors.code?.message}>
          {(p) => (
            <Input
              {...p}
              {...register('code')}
              placeholder="MAIN, BR1, BR2…"
              autoCapitalize="characters"
              disabled={!!initial}
            />
          )}
        </FormField>

        <FormField label="유형" required error={errors.kind?.message}>
          {(p) => <Select {...p} {...register('kind')} options={KIND_OPTIONS} />}
        </FormField>
      </div>

      <FormField label="도서관 이름" required error={errors.name?.message}>
        {(p) => <Input {...p} {...register('name')} placeholder="중앙도서관" />}
      </FormField>

      {kind !== 'MAIN' && (
        <FormField
          label="상위 본관"
          error={errors.parentId?.message}
          helpText="분관·이동도서관·협력기관은 상위 본관을 지정할 수 있습니다."
        >
          {(p) => <Select {...p} {...register('parentId')} options={parentOptions} />}
        </FormField>
      )}

      <FormField label="주소" error={errors.address?.message}>
        {(p) => <Input {...p} {...register('address')} placeholder="서울특별시 …" />}
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="대표 전화" error={errors.phone?.message}>
          {(p) => <Input {...p} {...register('phone')} placeholder="02-1234-5678" />}
        </FormField>
        <FormField label="대표 이메일" error={errors.email?.message}>
          {(p) => <Input {...p} {...register('email')} type="email" placeholder="info@..." />}
        </FormField>
      </div>

      <FormField label="운영 시간" error={errors.openHours?.message}>
        {(p) => <Input {...p} {...register('openHours')} placeholder="09:00~21:00" />}
      </FormField>
    </div>
  );
}

export const LibraryForm = forwardRef<LibraryFormHandle, LibraryFormProps>(LibraryFormInner);
