'use client';

import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorCard } from '@/components/ui/error-card';
import { Kpi } from '@/components/ui/kpi';
import { Skeleton } from '@/components/ui/skeleton';
import { StatRow } from '@/components/ui/stat-row';
import {
  useActiveSignals,
  useHoldings,
  useMarketSummary,
  usePortfolioSummary,
  useTopRecommendations,
} from '@/lib/api/queries/dashboard';
import { ROUTES } from '@/lib/constants';
import { cn } from '@/lib/utils/cn';
import { formatCurrency, formatPct, formatPnl, formatVolumeKR, pnlArrow, pnlClass } from '@/lib/utils/format';
import { useTradeModeStore } from '@/stores/trade-mode-store';

/**
 * 대시보드 페이지.
 * Designer의 dashboard.html을 1:1 변환하되, KPI/보유/시그널/추천을 TanStack Query로 연동.
 */
export default function DashboardPage() {
  const summary = usePortfolioSummary();
  const holdings = useHoldings();
  const market = useMarketSummary();
  const signals = useActiveSignals();
  const recos = useTopRecommendations();
  const mode = useTradeModeStore((s) => s.mode);

  return (
    <>
      <div className="page-title">
        <div className="page-title__text">
          <h1>대시보드</h1>
          <p>오늘의 시장 동향과 보유 종목을 한눈에 확인하세요.</p>
        </div>
        <div className="row gap-2">
          <Button variant="outline" size="sm" onClick={() => summary.refetch()}>
            새로고침
          </Button>
          <Link href={ROUTES.AUTO_TRADING}>
            <Button variant="primary" size="sm">
              자동매매 시작
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI 4종 */}
      <section className="grid-cols-4 mb-6">
        <KpiCard label="평가자산">
          {summary.data ? (
            <Kpi
              label="평가자산"
              value={
                <>
                  {formatCurrency(summary.data.total_asset, '').replace(/원$/, '')}{' '}
                  <span className="text-sm text-muted">원</span>
                </>
              }
              delta={
                <span className={pnlClass(summary.data.daily_pnl)}>
                  {pnlArrow(summary.data.daily_pnl)} {formatPnl(summary.data.daily_pnl)} (
                  {formatPct(summary.data.daily_pnl_pct)})
                </span>
              }
            />
          ) : (
            <KpiSkeleton />
          )}
        </KpiCard>
        <KpiCard label="금일 손익">
          {summary.data ? (
            <Kpi
              label="금일 손익"
              value={<span className={pnlClass(summary.data.daily_pnl)}>{formatPnl(summary.data.daily_pnl)}</span>}
              delta={
                <span className="text-muted">
                  실현 {formatPnl(summary.data.realized_today)} / 미실현 {formatPnl(summary.data.unrealized_today)}
                </span>
              }
            />
          ) : (
            <KpiSkeleton />
          )}
        </KpiCard>
        <KpiCard label="누적 수익률">
          {summary.data ? (
            <Kpi
              label="누적 수익률"
              value={<span className={pnlClass(summary.data.total_pnl_pct)}>{formatPct(summary.data.total_pnl_pct)}</span>}
              delta={<span className="text-up">▲ 0.32%p (vs 어제)</span>}
            />
          ) : (
            <KpiSkeleton />
          )}
        </KpiCard>
        <KpiCard label="활성 전략 / 시그널">
          {summary.data ? (
            <Kpi
              label="활성 전략 / 시그널"
              value={
                <>
                  {summary.data.active_strategies} <span className="text-sm text-muted">개 / </span>
                  {summary.data.active_signals}
                </>
              }
              delta={<Badge variant={mode === 'LIVE' ? 'live' : 'sim'} dot>{mode === 'LIVE' ? 'LIVE 모드' : 'SIM 모드'}</Badge>}
            />
          ) : (
            <KpiSkeleton />
          )}
        </KpiCard>
      </section>

      {/* 3컬럼 본문 */}
      <section
        className="grid"
        style={{ gridTemplateColumns: '5fr 4fr 3fr', gap: 'var(--space-4)' }}
        data-grid="dashboard-main"
      >
        {/* ===== 좌: 보유 종목 ===== */}
        <Card as="article">
          <Card.Header
            title="보유 종목"
            subtitle={`총 ${summary.data?.holdings_count ?? 0}종목 · 평가금액 ${formatCurrency(summary.data?.total_asset)}`}
            right={
              <Button variant="ghost" size="sm">
                전체 보기 →
              </Button>
            }
          />
          <Card.Body style={{ paddingTop: 'var(--space-2)', paddingBottom: 'var(--space-2)' }}>
            {holdings.isLoading && <SkeletonStockList />}
            {holdings.isError && <ErrorCard message="보유 종목을 불러올 수 없습니다." />}
            {holdings.data?.map((h) => (
              <div key={h.code} className="stock-row">
                <div className="stack">
                  <span className="stock-row__name">{h.name}</span>
                  <span className="stock-row__code">
                    {h.code} · {h.sector ?? '-'}
                    {h.delayed && (
                      <Badge variant="warning" className="ml-2 text-xs">
                        지연
                      </Badge>
                    )}
                  </span>
                </div>
                <div className="stock-row__price">
                  <div>{h.current_price.toLocaleString('ko-KR')}</div>
                  <div className="text-xs text-muted">평단 {h.avg_price.toLocaleString('ko-KR')}</div>
                </div>
                <div className="stock-row__delta">
                  <div className={pnlClass(h.pnl)}>{formatPnl(h.pnl)}</div>
                  <div className={cn('text-xs', pnlClass(h.pnl_pct))}>
                    {pnlArrow(h.pnl_pct)} {formatPct(Math.abs(h.pnl_pct))}
                  </div>
                </div>
              </div>
            ))}
          </Card.Body>
        </Card>

        {/* ===== 중: 시장 + 시그널 ===== */}
        <div className="stack gap-4">
          <Card as="article">
            <Card.Header title="시장 요약" right={<span className="text-subtle text-xs">5초마다 갱신</span>} />
            <Card.Body>
              {market.isLoading && <Skeleton height={120} />}
              {market.data && (
                <>
                  <div className="grid-cols-2">
                    <Kpi
                      label="KOSPI"
                      value={market.data.kospi.value.toLocaleString('ko-KR', { minimumFractionDigits: 2 })}
                      delta={
                        <span className={pnlClass(market.data.kospi.change)}>
                          {pnlArrow(market.data.kospi.change)} {formatNum(market.data.kospi.change)} ({formatPct(market.data.kospi.change_pct)})
                        </span>
                      }
                    />
                    <Kpi
                      label="KOSDAQ"
                      value={market.data.kosdaq.value.toLocaleString('ko-KR', { minimumFractionDigits: 2 })}
                      delta={
                        <span className={pnlClass(market.data.kosdaq.change)}>
                          {pnlArrow(market.data.kosdaq.change)} {formatNum(market.data.kosdaq.change)} ({formatPct(market.data.kosdaq.change_pct)})
                        </span>
                      }
                    />
                  </div>
                  <div className="divider" />
                  <div className="stack gap-2">
                    <StatRow label="코스피 거래대금" value={formatVolumeKR(market.data.kospi_volume_value)} />
                    <StatRow label="코스닥 거래대금" value={formatVolumeKR(market.data.kosdaq_volume_value)} />
                    <StatRow
                      label="외국인 순매수"
                      value={<span className={pnlClass(market.data.foreign_net)}>{formatVolumeKR(market.data.foreign_net)}</span>}
                    />
                    <StatRow
                      label="기관 순매수"
                      value={<span className={pnlClass(market.data.institution_net)}>{formatVolumeKR(market.data.institution_net)}</span>}
                    />
                  </div>
                </>
              )}
            </Card.Body>
          </Card>

          <Card as="article">
            <Card.Header
              title="진행중 시그널"
              right={
                <Link href={ROUTES.SIGNALS}>
                  <Button variant="ghost" size="sm">
                    전체 보기 →
                  </Button>
                </Link>
              }
            />
            <Card.Body style={{ paddingTop: 'var(--space-2)' }}>
              <ul className="stack gap-3">
                {signals.data?.map((s) => (
                  <li key={s.id} className="row items-center justify-between">
                    <div className="row items-center gap-3">
                      <Badge variant={s.action === 'BUY' ? 'up' : 'down'}>
                        {s.action === 'BUY' ? '매수' : '매도'}
                      </Badge>
                      <div className="stack">
                        <span className="text-strong fw-semibold">{s.name}</span>
                        <span className="text-xs text-subtle">
                          {s.strategy_name ?? s.source} · {new Date(s.created_at).toLocaleTimeString('ko-KR', { hour12: false, hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-num">{s.price.toLocaleString('ko-KR')}</div>
                      <div className={cn('text-xs', s.action === 'BUY' ? 'text-up' : 'text-info')}>
                        신뢰도 {s.confidence}%
                      </div>
                    </div>
                  </li>
                ))}
                {signals.isLoading && <SkeletonStockList />}
              </ul>
            </Card.Body>
          </Card>
        </div>

        {/* ===== 우: 추천주 TOP5 ===== */}
        <div className="stack gap-4">
          <Card as="article">
            <Card.Header
              title="추천주 TOP 5"
              right={
                <Link href={ROUTES.RECOMMENDATIONS}>
                  <Button variant="ghost" size="sm">
                    →
                  </Button>
                </Link>
              }
            />
            <Card.Body style={{ paddingTop: 'var(--space-2)', paddingBottom: 'var(--space-2)' }}>
              <ol className="stack">
                {recos.data?.map((r, i) => (
                  <li key={r.code} className="stock-row">
                    <div className="stack">
                      <span className="stock-row__name">
                        {i + 1}. {r.name}
                      </span>
                      <span className="stock-row__code">
                        {r.code} · {r.reason_text}
                      </span>
                    </div>
                    <Badge variant="success">{r.score}</Badge>
                    <span className={cn('text-num', pnlClass(r.change_pct))}>{formatPct(r.change_pct)}</span>
                  </li>
                ))}
                {recos.isLoading && <SkeletonStockList />}
              </ol>
            </Card.Body>
          </Card>

          <Card as="article">
            <Card.Header title="최근 알림" right={<Button variant="ghost" size="sm">모두 읽음</Button>} />
            <Card.Body style={{ paddingTop: 'var(--space-2)' }}>
              <ul className="stack gap-3">
                <li>
                  <div className="row items-center gap-2 mb-1">
                    <Badge variant="info">시그널</Badge>
                    <span className="text-xs text-subtle">14:21</span>
                  </div>
                  <p className="text-sm">삼성전자 골든크로스 시그널 발생</p>
                </li>
                <li>
                  <div className="row items-center gap-2 mb-1">
                    <Badge variant="warning">한도</Badge>
                    <span className="text-xs text-subtle">11:08</span>
                  </div>
                  <p className="text-sm">일일 매수 한도의 80% 사용</p>
                </li>
                <li>
                  <div className="row items-center gap-2 mb-1">
                    <Badge variant="success">체결</Badge>
                    <span className="text-xs text-subtle">09:32</span>
                  </div>
                  <p className="text-sm">현대차 10주 매수 체결 (235,000원)</p>
                </li>
              </ul>
            </Card.Body>
          </Card>
        </div>
      </section>

      <style jsx>{`
        @media (max-width: 1280px) {
          section[data-grid='dashboard-main'] {
            grid-template-columns: 6fr 6fr !important;
          }
          section[data-grid='dashboard-main'] > div:last-child {
            grid-column: 1 / -1;
          }
        }
        @media (max-width: 768px) {
          section[data-grid='dashboard-main'] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </>
  );
}

function KpiCard({ children }: { children: React.ReactNode; label?: string }) {
  return (
    <Card>
      <Card.Body>{children}</Card.Body>
    </Card>
  );
}

function KpiSkeleton() {
  return (
    <div className="stack gap-2">
      <Skeleton width={80} height={12} />
      <Skeleton width={140} height={24} />
      <Skeleton width={120} height={14} />
    </div>
  );
}

function SkeletonStockList() {
  return (
    <div className="stack gap-3 mt-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} height={36} />
      ))}
    </div>
  );
}

function formatNum(value: number): string {
  return value.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
