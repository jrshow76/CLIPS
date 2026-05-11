/**
 * Badge / Tag — 상태·카운트·필터 표시 (DSN-03 §3.7)
 *
 * Variants: solid / soft / outline × semantic 컬러
 * 도메인: 회원 상세(연체), 자료 카드(대출가능), 좌석맵(점유) 등
 */
import { cva, type VariantProps } from 'class-variance-authority';
import { forwardRef, type HTMLAttributes } from 'react';

import { cn } from '../../lib/cn';

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full font-medium whitespace-nowrap',
  {
    variants: {
      tone: {
        neutral: '',
        primary: '',
        success: '',
        warning: '',
        danger: '',
        info: '',
      },
      variant: {
        solid: '',
        soft: '',
        outline: 'border bg-transparent',
      },
      size: {
        sm: 'h-5 px-2 text-[11px]',
        md: 'h-6 px-2.5 text-[12px]',
        lg: 'h-7 px-3 text-[13px]',
      },
    },
    compoundVariants: [
      // solid
      { tone: 'neutral', variant: 'solid', className: 'bg-neutral-200 text-neutral-800' },
      { tone: 'primary', variant: 'solid', className: 'bg-primary-500 text-white' },
      { tone: 'success', variant: 'solid', className: 'bg-success text-white' },
      { tone: 'warning', variant: 'solid', className: 'bg-warning text-white' },
      { tone: 'danger', variant: 'solid', className: 'bg-danger text-white' },
      { tone: 'info', variant: 'solid', className: 'bg-info text-white' },
      // soft
      { tone: 'neutral', variant: 'soft', className: 'bg-neutral-100 text-neutral-700' },
      { tone: 'primary', variant: 'soft', className: 'bg-primary-50 text-primary-700' },
      { tone: 'success', variant: 'soft', className: 'bg-success-50 text-success' },
      { tone: 'warning', variant: 'soft', className: 'bg-warning-50 text-warning' },
      { tone: 'danger', variant: 'soft', className: 'bg-danger-50 text-danger' },
      { tone: 'info', variant: 'soft', className: 'bg-info-50 text-info' },
      // outline
      { tone: 'neutral', variant: 'outline', className: 'border-neutral-300 text-neutral-700' },
      { tone: 'primary', variant: 'outline', className: 'border-primary-500 text-primary-700' },
      { tone: 'success', variant: 'outline', className: 'border-success text-success' },
      { tone: 'warning', variant: 'outline', className: 'border-warning text-warning' },
      { tone: 'danger', variant: 'outline', className: 'border-danger text-danger' },
      { tone: 'info', variant: 'outline', className: 'border-info text-info' },
    ],
    defaultVariants: {
      tone: 'neutral',
      variant: 'soft',
      size: 'md',
    },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  { className, tone, variant, size, children, ...rest },
  ref,
) {
  return (
    <span ref={ref} className={cn(badgeVariants({ tone, variant, size }), className)} {...rest}>
      {children}
    </span>
  );
});
