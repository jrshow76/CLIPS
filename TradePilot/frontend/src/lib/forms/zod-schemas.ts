import { z } from 'zod';

/**
 * 공통 zod 스키마 모음.
 * - 비밀번호 정책 (docs/14_exception_policy E0055): 8~32자, 영문/숫자/특수문자 각 1자 이상.
 * - 모든 message는 한글.
 */

export const emailSchema = z
  .string({ required_error: '이메일을 입력해주세요.' })
  .min(1, '이메일을 입력해주세요.')
  .email('올바른 이메일 형식이 아닙니다.');

export const passwordSchema = z
  .string({ required_error: '비밀번호를 입력해주세요.' })
  .min(8, '비밀번호는 8자 이상이어야 합니다.')
  .max(32, '비밀번호는 32자 이하여야 합니다.')
  .regex(/[A-Za-z]/, '비밀번호에 영문이 포함되어야 합니다.')
  .regex(/[0-9]/, '비밀번호에 숫자가 포함되어야 합니다.')
  .regex(/[^A-Za-z0-9]/, '비밀번호에 특수문자가 포함되어야 합니다.');

export const nicknameSchema = z
  .string({ required_error: '닉네임을 입력해주세요.' })
  .min(2, '닉네임은 2자 이상이어야 합니다.')
  .max(16, '닉네임은 16자 이하여야 합니다.');

export const otpSchema = z
  .string({ required_error: 'OTP를 입력해주세요.' })
  .regex(/^\d{6}$/, 'OTP는 숫자 6자리여야 합니다.');

export const stockCodeSchema = z
  .string({ required_error: '종목코드를 입력해주세요.' })
  .regex(/^\d{6}$/, '종목코드는 숫자 6자리여야 합니다.');

export const positiveIntSchema = z
  .number({ invalid_type_error: '숫자를 입력해주세요.' })
  .int('정수만 입력 가능합니다.')
  .positive('0보다 큰 값을 입력해주세요.');

export const nonNegativeNumberSchema = z
  .number({ invalid_type_error: '숫자를 입력해주세요.' })
  .min(0, '0 이상이어야 합니다.');

/* ============================================================
 *  비밀번호 정책 체크리스트 (UI 표시용)
 * ============================================================ */
export interface PasswordChecks {
  length: boolean;
  alpha: boolean;
  digit: boolean;
  special: boolean;
}

export function evaluatePassword(pw: string): PasswordChecks {
  return {
    length: pw.length >= 8 && pw.length <= 32,
    alpha: /[A-Za-z]/.test(pw),
    digit: /[0-9]/.test(pw),
    special: /[^A-Za-z0-9]/.test(pw),
  };
}

/* ============================================================
 *  도메인별 폼 스키마
 * ============================================================ */
export const loginFormSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, '비밀번호를 입력해주세요.'),
  remember: z.boolean().optional(),
});
export type LoginForm = z.infer<typeof loginFormSchema>;

export const signupFormSchema = z
  .object({
    email: emailSchema,
    nickname: nicknameSchema,
    password: passwordSchema,
    password_confirm: z.string({ required_error: '비밀번호 확인을 입력해주세요.' }),
    agree_terms: z.boolean().refine((v) => v === true, '이용약관에 동의해주세요.'),
    agree_privacy: z.boolean().refine((v) => v === true, '개인정보 처리방침에 동의해주세요.'),
  })
  .refine((v) => v.password === v.password_confirm, {
    path: ['password_confirm'],
    message: '비밀번호가 일치하지 않습니다.',
  });
export type SignupForm = z.infer<typeof signupFormSchema>;

export const forgotPasswordSchema = z.object({
  email: emailSchema,
});
export type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    token: z.string().min(1, '재설정 토큰이 없습니다.'),
    password: passwordSchema,
    password_confirm: z.string().min(1, '비밀번호 확인을 입력해주세요.'),
  })
  .refine((v) => v.password === v.password_confirm, {
    path: ['password_confirm'],
    message: '비밀번호가 일치하지 않습니다.',
  });
export type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;

export const otpFormSchema = z.object({
  otp: otpSchema,
});
export type OtpForm = z.infer<typeof otpFormSchema>;

export const orderFormSchema = z
  .object({
    code: stockCodeSchema,
    side: z.enum(['BUY', 'SELL']),
    order_type: z.enum(['MARKET', 'LIMIT']),
    qty: z.coerce.number({ invalid_type_error: '수량을 입력해주세요.' }).int().positive('수량은 1 이상이어야 합니다.'),
    price: z.coerce.number().nonnegative('가격은 0 이상이어야 합니다.').optional(),
  })
  .refine((v) => v.order_type !== 'LIMIT' || (typeof v.price === 'number' && v.price > 0), {
    path: ['price'],
    message: '지정가 주문에는 가격이 필요합니다.',
  });
export type OrderForm = z.infer<typeof orderFormSchema>;

export const strategyConditionSchema = z.object({
  indicator: z.string().min(1, '지표를 선택해주세요.'),
  operator: z.enum(['<', '<=', '=', '>=', '>', 'CROSS_UP', 'CROSS_DOWN']),
  value: z.coerce.number({ invalid_type_error: '값을 숫자로 입력해주세요.' }),
});

export const strategyRuleSchema = z.object({
  side: z.enum(['BUY', 'SELL']),
  conditions: z.array(strategyConditionSchema).min(1, '조건을 1개 이상 추가해주세요.'),
  qty_mode: z.enum(['FIXED', 'PERCENT', 'KELLY']),
  qty_value: z.coerce.number().positive('수량/비율은 0보다 커야 합니다.'),
});

export const strategyFormSchema = z.object({
  name: z.string().min(2, '전략명은 2자 이상이어야 합니다.').max(32, '전략명은 32자 이하여야 합니다.'),
  description: z.string().max(200).optional(),
  universe: z.array(z.string()).min(1, '대상 종목을 1개 이상 추가해주세요.'),
  rules: z.array(strategyRuleSchema).min(1, '규칙을 1개 이상 추가해주세요.'),
  max_position_pct: z.coerce.number().min(0).max(100).optional(),
  daily_loss_limit: z.coerce.number().optional(),
});
export type StrategyForm = z.infer<typeof strategyFormSchema>;

export const tradingLimitsSchema = z.object({
  daily_buy_limit: z.coerce.number().nonnegative('0 이상 입력해주세요.'),
  daily_loss_limit: z.coerce.number().nonpositive('손실 한도는 0 이하(음수)로 입력해주세요.'),
  max_position_pct: z.coerce.number().min(0, '0 이상').max(100, '100 이하'),
  per_order_limit: z.coerce.number().nonnegative(),
});
export type TradingLimitsForm = z.infer<typeof tradingLimitsSchema>;

export const backtestFormSchema = z.object({
  strategy_id: z.string().min(1, '전략을 선택해주세요.'),
  from: z.string().min(1, '시작일을 선택해주세요.'),
  to: z.string().min(1, '종료일을 선택해주세요.'),
  initial_cash: z.coerce.number().positive('초기 자본은 0보다 커야 합니다.'),
  slippage_bps: z.coerce.number().min(0).max(1000).optional(),
  fee_bps: z.coerce.number().min(0).max(1000).optional(),
});
export type BacktestForm = z.infer<typeof backtestFormSchema>;

export const signalRuleFormSchema = z.object({
  name: z.string().min(1, '규칙명을 입력해주세요.'),
  indicator: z.string().min(1, '지표를 선택해주세요.'),
  operator: z.enum(['<', '<=', '=', '>=', '>', 'CROSS_UP', 'CROSS_DOWN']),
  value: z.coerce.number(),
  enabled: z.boolean(),
  notify_channel: z.enum(['WEB', 'EMAIL', 'PUSH']),
});
export type SignalRuleForm = z.infer<typeof signalRuleFormSchema>;
