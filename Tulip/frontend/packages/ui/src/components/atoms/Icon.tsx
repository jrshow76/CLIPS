/**
 * Icon — 아이콘 래퍼.
 *
 * 라이브러리는 `lucide-react`를 단일 채택 (DSN-02 §5).
 * 사이즈 토큰: xs=12 / sm=16 / md=20 / lg=24 / xl=32 (stroke 1.5).
 *
 * @example
 *   import { Search } from 'lucide-react';
 *   <Icon as={Search} size="md" />
 */
import { forwardRef, type ComponentType, type HTMLAttributes, type ReactElement } from 'react';
import type { LucideProps } from 'lucide-react';

import { cn } from '../../lib/cn';

export type IconSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

const sizeMap: Record<IconSize, number> = {
  xs: 12,
  sm: 16,
  md: 20,
  lg: 24,
  xl: 32,
};

export interface IconProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'children'> {
  /** Lucide icon 컴포넌트 */
  as: ComponentType<LucideProps>;
  size?: IconSize;
  /** 장식용 (스크린리더 무시) */
  decorative?: boolean;
  /** 의미 전달 시 라벨 */
  label?: string;
  strokeWidth?: number;
}

export function Icon({
  as: IconComponent,
  size = 'md',
  decorative = true,
  label,
  strokeWidth = 1.5,
  className,
  ...rest
}: IconProps): ReactElement {
  const px = sizeMap[size];
  return (
    <span
      role={decorative ? undefined : 'img'}
      aria-hidden={decorative || undefined}
      aria-label={!decorative ? label : undefined}
      className={cn('inline-flex shrink-0 align-middle', className)}
      {...rest}
    >
      <IconComponent size={px} strokeWidth={strokeWidth} aria-hidden="true" />
    </span>
  );
}

// forwardRef 미사용 (간단 컴포넌트). 필요 시 추후 추가.
export const _ForwardRefIcon = forwardRef<HTMLSpanElement, IconProps>(function _ForwardRefIcon(
  props,
  _ref,
) {
  return <Icon {...props} />;
});
