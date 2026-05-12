import { type ReactNode } from 'react';

/**
 * 비로그인 영역(로그인/회원가입) 레이아웃.
 * - 헤더/사이드바 없음.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
