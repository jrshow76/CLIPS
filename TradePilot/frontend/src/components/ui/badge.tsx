import { type HTMLAttributes, type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export type BadgeVariant =
  | 'default'
  | 'up'
  | 'down'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'sim'
  | 'live';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  dot?: boolean;
  children?: ReactNode;
}

const variantClass: Record<BadgeVariant, string> = {
  default: '',
  up: 'badge--up',
  down: 'badge--down',
  success: 'badge--success',
  warning: 'badge--warning',
  danger: 'badge--danger',
  info: 'badge--info',
  sim: 'badge--sim',
  live: 'badge--live',
};

export function Badge({ variant = 'default', dot, className, children, ...rest }: BadgeProps) {
  return (
    <span className={cn('badge', variantClass[variant], dot && 'badge-dot', className)} {...rest}>
      {children}
    </span>
  );
}
