import { type HTMLAttributes, type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export type BannerVariant = 'default' | 'live' | 'warning' | 'info';

export interface BannerProps extends HTMLAttributes<HTMLDivElement> {
  variant?: BannerVariant;
  icon?: ReactNode;
  children: ReactNode;
}

const variantClass: Record<BannerVariant, string> = {
  default: '',
  live: 'banner--live',
  warning: 'banner--warning',
  info: 'banner--info',
};

export function Banner({ variant = 'default', icon, className, children, ...rest }: BannerProps) {
  return (
    <div className={cn('banner', variantClass[variant], className)} role="status" {...rest}>
      {icon && <span aria-hidden="true">{icon}</span>}
      <span>{children}</span>
    </div>
  );
}
