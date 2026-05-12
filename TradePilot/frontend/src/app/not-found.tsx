import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { ROUTES } from '@/lib/constants';

export default function NotFound() {
  return (
    <div className="center" style={{ minHeight: '100vh' }}>
      <EmptyState
        icon="?"
        title="페이지를 찾을 수 없습니다."
        description="주소를 다시 확인하거나 대시보드로 이동해주세요."
        action={
          <Link href={ROUTES.DASHBOARD}>
            <Button variant="primary">대시보드로 이동</Button>
          </Link>
        }
      />
    </div>
  );
}
