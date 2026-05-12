import { redirect } from 'next/navigation';

import { ROUTES } from '@/lib/constants';

/**
 * 루트(/) 진입 시 대시보드로 리다이렉트.
 * 인증 미보유 시 (app) layout 가드가 /login으로 다시 보냄.
 */
export default function HomePage(): never {
  redirect(ROUTES.DASHBOARD);
}
