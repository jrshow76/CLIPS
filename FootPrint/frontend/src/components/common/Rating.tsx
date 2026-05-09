'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';

interface RatingProps {
  value?: number;
  onChange?: (value: number) => void;
  readOnly?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeMap = {
  sm: 'text-[16px]',
  md: 'text-[24px]',
  lg: 'text-[28px]',
};

export default function Rating({
  value = 0,
  onChange,
  readOnly = false,
  size = 'md',
  className,
}: RatingProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const displayValue = hovered ?? value;

  return (
    <div className={cn('flex gap-1', className)}>
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={readOnly}
          onClick={() => !readOnly && onChange?.(star)}
          onMouseEnter={() => !readOnly && setHovered(star)}
          onMouseLeave={() => !readOnly && setHovered(null)}
          className={cn(
            sizeMap[size],
            'transition-colors leading-none',
            readOnly ? 'cursor-default' : 'cursor-pointer',
            star <= displayValue ? 'text-[#F59E0B]' : 'text-[#E7E5E4]'
          )}
        >
          ★
        </button>
      ))}
    </div>
  );
}
