import { cn } from '@/lib/utils';

interface BadgeProps {
  label: string;
  color?: string;
  className?: string;
}

/**
 * color prop: hex 색상값 또는 'orange' | 'green' | 'blue' 프리셋
 * 디자인 시스템의 badge 스타일을 유지한다.
 */
export default function Badge({ label, color, className }: BadgeProps) {
  const preset: Record<string, string> = {
    orange: 'bg-[#FFF8F0] text-[#F97316]',
    green: 'bg-[#F0FDF4] text-[#16A34A]',
    blue: 'bg-[#F0F9FF] text-[#0284C7]',
    yellow: 'bg-[#FFFBEB] text-[#D97706]',
    purple: 'bg-[#FAF5FF] text-[#7C3AED]',
    red: 'bg-[#FEF2F2] text-[#DC2626]',
  };

  const presetClass = color ? preset[color] : undefined;

  return (
    <span
      className={cn(
        'inline-block px-2.5 py-[3px] rounded-full text-[11px] font-bold',
        presetClass ?? 'bg-[#FFF8F0] text-[#F97316]',
        className
      )}
      style={!presetClass && color ? { backgroundColor: `${color}20`, color } : undefined}
    >
      {label}
    </span>
  );
}
