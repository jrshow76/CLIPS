import { type HTMLAttributes, type ReactNode } from 'react';

import { cn } from '@/lib/utils/cn';

export interface CardProps extends HTMLAttributes<HTMLElement> {
  compact?: boolean;
  ghost?: boolean;
  as?: 'section' | 'article' | 'div';
}

/**
 * Designer .card 매핑.
 *  - <Card.Header>, <Card.Body>, <Card.Footer>를 통해 BEM 자식 클래스 적용.
 *  - compact: 패딩 축소. ghost: 점선 보더, 투명 배경 (빈 상태/플레이스홀더).
 */
export function Card({ compact, ghost, as = 'section', className, children, ...rest }: CardProps) {
  const Tag = as;
  return (
    <Tag className={cn('card', compact && 'card--compact', ghost && 'card--ghost', className)} {...rest}>
      {children}
    </Tag>
  );
}

interface SectionProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
}

Card.Header = function CardHeader({ title, subtitle, right, className, children, ...rest }: SectionProps) {
  return (
    <header className={cn('card__header', className)} {...rest}>
      {(title || subtitle) && (
        <div>
          {title && <h3 className="card__title">{title}</h3>}
          {subtitle && <p className="card__subtitle">{subtitle}</p>}
        </div>
      )}
      {children}
      {right && <div>{right}</div>}
    </header>
  );
};

Card.Body = function CardBody({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('card__body', className)} {...rest}>
      {children}
    </div>
  );
};

Card.Footer = function CardFooter({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <footer className={cn('card__footer', className)} {...rest}>
      {children}
    </footer>
  );
};
