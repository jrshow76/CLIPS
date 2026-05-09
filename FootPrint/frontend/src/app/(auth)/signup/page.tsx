'use client';

import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '@/lib/hooks/useAuth';
import { useToast } from '@/components/common/useToast';
import Input from '@/components/common/Input';
import Button from '@/components/common/Button';
import ToastContainer from '@/components/common/Toast';

const schema = z.object({
  email: z.string().min(1, '이메일을 입력하세요').email('올바른 이메일 형식이 아닙니다'),
  password: z
    .string()
    .min(8, '비밀번호는 8자 이상이어야 합니다')
    .max(100, '최대 100자'),
  passwordConfirm: z.string().min(1, '비밀번호 확인을 입력하세요'),
  nickname: z.string().min(2, '닉네임은 2자 이상이어야 합니다').max(20, '최대 20자'),
}).refine((d) => d.password === d.passwordConfirm, {
  path: ['passwordConfirm'],
  message: '비밀번호가 일치하지 않습니다',
});

type FormValues = z.infer<typeof schema>;

export default function SignupPage() {
  const { signupMutation } = useAuth();
  const toast = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    try {
      await signupMutation.mutateAsync({
        email: values.email,
        password: values.password,
        nickname: values.nickname,
      });
      toast.success('회원가입이 완료되었습니다. 로그인해주세요.');
    } catch {
      toast.error('회원가입에 실패했습니다. 이미 사용 중인 이메일일 수 있습니다.');
    }
  };

  return (
    <>
      <main className="bg-white rounded-[20px] shadow-[0_20px_60px_rgba(0,0,0,0.12)] px-10 py-12 w-full max-w-[440px] max-sm:px-6 max-sm:py-9 max-sm:mx-4">
        {/* 로고 */}
        <div className="text-center mb-8">
          <span className="text-[48px] block mb-2">🗺️</span>
          <h1 className="text-[24px] font-bold text-[#EA580C] tracking-tight">발자국</h1>
          <p className="text-[14px] text-[#78716C] mt-1">나의 장소 기록을 시작하세요</p>
        </div>

        {/* 폼 */}
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
          <Input
            label="이메일"
            type="email"
            placeholder="이메일을 입력하세요"
            autoComplete="email"
            register={register('email')}
            error={errors.email?.message}
          />
          <Input
            label="닉네임"
            placeholder="닉네임을 입력하세요 (2~20자)"
            autoComplete="nickname"
            register={register('nickname')}
            error={errors.nickname?.message}
          />
          <Input
            label="비밀번호"
            type="password"
            placeholder="비밀번호를 입력하세요 (8자 이상)"
            autoComplete="new-password"
            register={register('password')}
            error={errors.password?.message}
          />
          <Input
            label="비밀번호 확인"
            type="password"
            placeholder="비밀번호를 한 번 더 입력하세요"
            autoComplete="new-password"
            register={register('passwordConfirm')}
            error={errors.passwordConfirm?.message}
          />
          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            loading={isSubmitting}
            className="mt-2"
          >
            회원가입
          </Button>
        </form>

        {/* 하단 링크 */}
        <p className="text-center mt-6 text-[14px] text-[#78716C]">
          이미 계정이 있으신가요?{' '}
          <Link href="/login" className="text-[#F97316] font-semibold hover:underline">
            로그인
          </Link>
        </p>
      </main>
      <ToastContainer />
    </>
  );
}
