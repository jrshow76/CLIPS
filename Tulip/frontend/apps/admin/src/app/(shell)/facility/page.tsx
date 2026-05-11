import { redirect } from 'next/navigation';

export const metadata = { title: '시설 — Tulip+ Admin' };

/**
 * /facility 진입 시 도서관 관리 목록으로 리다이렉트.
 *
 * 좌석·시설예약 등 Phase 2 화면이 추가되면 별도 인덱스로 분리한다.
 */
export default function FacilityIndexPage() {
  redirect('/facility/libraries');
}
