/**
 * AccessDenied — 권한 부족 안내.
 *
 * 사용처: useHasScope/useHasRole 검사 실패 시 화면 본문 대체.
 */
import { ShieldX } from 'lucide-react';
import { type ReactNode } from 'react';

import { Icon } from '../atoms/Icon';

import { EmptyState } from './EmptyState';

export interface AccessDeniedProps {
  /** 필요한 권한 설명 (예: "회원 관리 권한") */
  requiredScope?: string;
  title?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}

export function AccessDenied({
  requiredScope,
  title = '접근 권한이 없습니다',
  description,
  action,
}: AccessDeniedProps) {
  return (
    <EmptyState
      icon={<Icon as={ShieldX} size="xl" />}
      title={title}
      description={
        description ??
        (requiredScope
          ? `이 화면을 이용하려면 ${requiredScope} 권한이 필요합니다. 관리자에게 문의하세요.`
          : '이 화면을 이용하려면 추가 권한이 필요합니다. 관리자에게 문의하세요.')
      }
      primaryAction={action}
    />
  );
}
