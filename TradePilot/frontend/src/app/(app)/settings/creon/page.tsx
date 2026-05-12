'use client';

import { CheckCircle2, Plug, RefreshCw, XCircle } from 'lucide-react';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Kpi } from '@/components/ui/kpi';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { StatRow } from '@/components/ui/stat-row';
import { useCreonStatus, useTestCreonConnection } from '@/lib/api/queries/creon';
import { ROUTES } from '@/lib/constants';
import { formatKST } from '@/lib/utils/date';

export default function CreonSettingsPage() {
  const status = useCreonStatus();
  const test = useTestCreonConnection();

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>크레온 게이트웨이</h1>
          <p>증권사 게이트웨이 연결 상태와 일일 요청 한도를 확인합니다.</p>
        </div>
        <Link href={ROUTES.SETTINGS}><Button variant="outline">← 설정</Button></Link>
      </div>

      {status.isLoading && <Skeleton height={300} />}
      {status.isError && <ErrorCard message="크레온 상태를 확인할 수 없습니다." />}

      {status.data && (
        <div className="grid-cols-2">
          <Card>
            <Card.Header
              title={<span className="row items-center gap-2"><Plug className="h-4 w-4" /> 연결 상태</span>}
              right={
                status.data.connected ? (
                  <Badge variant="success" dot>연결됨</Badge>
                ) : (
                  <Badge variant="danger" dot>연결 끊김</Badge>
                )
              }
            />
            <Card.Body className="stack gap-3">
              <div className="row items-center gap-3">
                {status.data.connected ? (
                  <CheckCircle2 className="text-up h-8 w-8" />
                ) : (
                  <XCircle className="text-down h-8 w-8" />
                )}
                <div>
                  <p className="text-strong fw-semibold">
                    {status.data.connected ? '게이트웨이 정상 동작 중' : '게이트웨이 연결 실패'}
                  </p>
                  <p className="text-subtle text-xs">마지막 응답: {formatKST(status.data.last_heartbeat)}</p>
                </div>
              </div>
              <div className="divider" />
              <StatRow label="계좌번호" value={status.data.account_no} />
              <StatRow label="별칭" value={status.data.account_alias ?? '-'} />
              <StatRow label="응답 지연" value={`${status.data.latency_ms}ms`} />
            </Card.Body>
            <Card.Footer>
              <div className="row gap-2 justify-end">
                <Button
                  variant="outline"
                  leftIcon={<RefreshCw className="h-4 w-4" />}
                  onClick={() => test.mutate()}
                  loading={test.isPending}
                >
                  연결 테스트
                </Button>
              </div>
            </Card.Footer>
          </Card>

          <Card>
            <Card.Header title="일일 요청 한도" />
            <Card.Body className="stack gap-3">
              <Kpi
                label="오늘 사용량"
                value={
                  <>
                    {status.data.daily_request_count.toLocaleString('ko-KR')} / {status.data.daily_request_limit.toLocaleString('ko-KR')}
                    <span className="text-sm text-muted ml-1">건</span>
                  </>
                }
              />
              <Progress
                value={(status.data.daily_request_count / status.data.daily_request_limit) * 100}
                variant={
                  status.data.daily_request_count / status.data.daily_request_limit >= 0.8 ? 'danger' : 'default'
                }
                label="일일 한도 사용률"
              />
              <p className="text-xs text-subtle">
                일일 한도 도달 시 신규 주문/시세 호출이 차단됩니다. (E0008)
              </p>
            </Card.Body>
          </Card>
        </div>
      )}
    </>
  );
}
