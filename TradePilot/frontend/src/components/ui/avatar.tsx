import { cn } from '@/lib/utils/cn';

export interface AvatarProps {
  name: string;
  size?: number;
  className?: string;
}

export function Avatar({ name, size = 28, className }: AvatarProps) {
  const initial = name.slice(0, 1);
  return (
    <span
      className={cn('avatar', className)}
      style={{ width: size, height: size, fontSize: Math.max(10, Math.floor(size * 0.4)) }}
      aria-hidden="true"
    >
      {initial}
    </span>
  );
}
