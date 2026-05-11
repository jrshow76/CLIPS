'use client';

/**
 * SearchBar — OPAC 통합검색·헤더 검색·Command Palette 공용 (DSN-03 §4.2)
 *
 * Variants: hero (OPAC홈) / default / compact (헤더)
 * a11y: role=combobox 대비 (자동완성은 별도 listbox 컴포넌트로 추후 확장).
 */
import { Search } from 'lucide-react';
import { forwardRef, type FormEvent, type InputHTMLAttributes } from 'react';

import { cn } from '../../lib/cn';
import { Button } from '../atoms/Button';
import { Icon } from '../atoms/Icon';

export type SearchBarVariant = 'hero' | 'default' | 'compact';

export interface SearchBarProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  variant?: SearchBarVariant;
  /** 검색 버튼 라벨 */
  submitLabel?: string;
  /** 제출 핸들러 (form submit) */
  onSearch?: (value: string) => void;
}

const variantStyles: Record<SearchBarVariant, string> = {
  hero: 'h-14 text-[18px] rounded-2xl pl-14 pr-32',
  default: 'h-12 text-[15px] rounded-xl pl-12 pr-28',
  compact: 'h-9 text-[13px] rounded-md pl-9 pr-20',
};

const iconPos: Record<SearchBarVariant, string> = {
  hero: 'left-5 top-1/2 -translate-y-1/2',
  default: 'left-4 top-1/2 -translate-y-1/2',
  compact: 'left-2.5 top-1/2 -translate-y-1/2',
};

const buttonPos: Record<SearchBarVariant, string> = {
  hero: 'right-2 top-1/2 -translate-y-1/2',
  default: 'right-1.5 top-1/2 -translate-y-1/2',
  compact: 'right-1 top-1/2 -translate-y-1/2',
};

export const SearchBar = forwardRef<HTMLInputElement, SearchBarProps>(function SearchBar(
  { variant = 'default', submitLabel = '검색', onSearch, className, defaultValue, ...rest },
  ref,
) {
  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const value = String(data.get('q') ?? '');
    onSearch?.(value);
  }

  return (
    <form
      role="search"
      onSubmit={handleSubmit}
      className={cn('relative w-full', className)}
    >
      <span
        aria-hidden="true"
        className={cn('pointer-events-none absolute text-neutral-500', iconPos[variant])}
      >
        <Icon as={Search} size={variant === 'compact' ? 'sm' : 'md'} />
      </span>
      <input
        ref={ref}
        name="q"
        type="search"
        defaultValue={defaultValue}
        aria-label="검색어 입력"
        className={cn(
          'w-full border border-neutral-300 bg-surface-card text-neutral-900 placeholder:text-neutral-500',
          'focus-visible:outline-none focus-visible:shadow-focus focus-visible:border-primary-500',
          'shadow-sm transition-colors',
          variantStyles[variant],
        )}
        {...rest}
      />
      <span className={cn('absolute', buttonPos[variant])}>
        <Button
          type="submit"
          size={variant === 'compact' ? 'sm' : variant === 'hero' ? 'lg' : 'md'}
          variant="primary"
        >
          {submitLabel}
        </Button>
      </span>
    </form>
  );
});
