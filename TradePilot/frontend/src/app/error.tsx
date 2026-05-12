'use client';

import { Button } from '@/components/ui/button';
import { ErrorCard } from '@/components/ui/error-card';

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="center" style={{ minHeight: '100vh' }}>
      <div style={{ maxWidth: 480 }}>
        <ErrorCard
          title="문제가 발생했습니다."
          message={error.message || '예기치 않은 오류로 페이지를 표시할 수 없습니다.'}
          code={error.digest}
          action={
            <Button variant="primary" onClick={reset}>
              다시 시도
            </Button>
          }
        />
      </div>
    </div>
  );
}
