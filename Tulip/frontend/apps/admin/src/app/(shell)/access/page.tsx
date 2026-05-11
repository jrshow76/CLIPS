import { redirect } from 'next/navigation';

export const metadata = { title: '회원/이용 — Tulip+ Admin' };

/**
 * /access 진입 시 회원 관리 목록으로 리다이렉트.
 *
 * Phase 2 이후 출입·접근통제 화면이 추가되면 별도 인덱스로 분리한다.
 */
export default function AccessIndexPage() {
  redirect('/access/members');
}
