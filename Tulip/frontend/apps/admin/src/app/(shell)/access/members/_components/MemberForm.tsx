'use client';

/**
 * MemberForm — 회원 등록·수정 공용 폼.
 *
 * - react-hook-form + zod 검증
 * - 부모가 FormModal 등으로 감싸 사용하므로 본 컴포넌트는 form 태그를 직접 렌더하지 않는다.
 *   부모가 form을 렌더하고, ref로 noop 또는 onSubmit을 전달받는 패턴.
 *
 * 사용:
 *   const ref = useRef<MemberFormHandle>(null);
 *   <FormModal onSubmit={() => ref.current?.submit()}>
 *     <MemberForm ref={ref} onValid={(v) => mutate(v)} />
 *   </FormModal>
 */
import { zodResolver } from '@hookform/resolvers/zod';
import {
  type Member,
  type CreateMemberInput,
  type UpdateMemberInput,
  useLibrariesQuery,
} from '@tulip/api-client';
import { FormField, Input, Select } from '@tulip/ui';
import {
  forwardRef,
  useImperativeHandle,
  type ForwardedRef,
} from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

const memberSchema = z.object({
  name: z.string().min(1, '이름을 입력하세요.').max(50, '이름은 50자 이내로 입력하세요.'),
  email: z
    .string()
    .email('올바른 이메일 형식이 아닙니다.')
    .optional()
    .or(z.literal('').transform(() => undefined)),
  phone: z
    .string()
    .regex(/^[0-9-+\s]*$/, '연락처는 숫자·하이픈만 사용할 수 있습니다.')
    .max(20)
    .optional()
    .or(z.literal('').transform(() => undefined)),
  birthDate: z.string().optional().or(z.literal('').transform(() => undefined)),
  memberType: z.enum(['ADULT', 'YOUTH', 'CHILD', 'STAFF', 'GUEST']),
  libraryId: z.string().min(1, '소속 도서관을 선택하세요.'),
});

export type MemberFormValues = z.infer<typeof memberSchema>;

export interface MemberFormHandle {
  /** 외부에서 submit 트리거. 검증 통과 시 onValid 호출 */
  submit: () => void;
}

export interface MemberFormProps {
  initial?: Member;
  onValid: (values: CreateMemberInput | UpdateMemberInput) => void;
}

const MEMBER_TYPE_OPTIONS = [
  { value: 'ADULT', label: '성인' },
  { value: 'YOUTH', label: '청소년' },
  { value: 'CHILD', label: '어린이' },
  { value: 'STAFF', label: '직원' },
  { value: 'GUEST', label: '게스트' },
];

function MemberFormInner(
  { initial, onValid }: MemberFormProps,
  ref: ForwardedRef<MemberFormHandle>,
) {
  const librariesQuery = useLibrariesQuery({ size: 100 });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<MemberFormValues>({
    resolver: zodResolver(memberSchema),
    defaultValues: initial
      ? {
          name: initial.name,
          email: initial.email ?? undefined,
          phone: initial.phone ?? undefined,
          birthDate: initial.birthDate ?? undefined,
          memberType: initial.memberType,
          libraryId: initial.libraryId,
        }
      : {
          name: '',
          email: undefined,
          phone: undefined,
          birthDate: undefined,
          memberType: 'ADULT',
          libraryId: '',
        },
  });

  useImperativeHandle(ref, () => ({
    submit: () => {
      void handleSubmit((values) => onValid(values as CreateMemberInput))();
    },
  }));

  const libraryOptions = (librariesQuery.data?.items ?? []).map((l) => ({
    value: l.id,
    label: l.name,
  }));

  return (
    <div className="flex flex-col gap-4">
      <FormField label="이름" required error={errors.name?.message}>
        {(p) => <Input {...p} {...register('name')} placeholder="홍길동" />}
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="회원 유형" required error={errors.memberType?.message}>
          {(p) => (
            <Select
              {...p}
              {...register('memberType')}
              options={MEMBER_TYPE_OPTIONS}
              aria-label="회원 유형"
            />
          )}
        </FormField>

        <FormField
          label="소속 도서관"
          required
          error={errors.libraryId?.message}
          helpText={librariesQuery.isLoading ? '도서관 목록 불러오는 중…' : undefined}
        >
          {(p) => (
            <Select
              {...p}
              {...register('libraryId')}
              options={libraryOptions}
              placeholder="선택"
            />
          )}
        </FormField>
      </div>

      <FormField label="이메일" error={errors.email?.message}>
        {(p) => (
          <Input
            {...p}
            {...register('email')}
            type="email"
            placeholder="email@example.com"
            autoComplete="email"
          />
        )}
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="연락처" error={errors.phone?.message}>
          {(p) => (
            <Input
              {...p}
              {...register('phone')}
              type="tel"
              placeholder="010-1234-5678"
              autoComplete="tel"
            />
          )}
        </FormField>

        <FormField label="생년월일" error={errors.birthDate?.message}>
          {(p) => <Input {...p} {...register('birthDate')} type="date" />}
        </FormField>
      </div>
    </div>
  );
}

export const MemberForm = forwardRef<MemberFormHandle, MemberFormProps>(MemberFormInner);
