'use client';

import {
  Activity,
  BarChart3,
  Cog,
  LayoutDashboard,
  LineChart,
  LogOut,
  PieChart,
  Sigma,
  Star,
  Timer,
  type LucideIcon,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { ROUTES } from '@/lib/constants';
import { cn } from '@/lib/utils/cn';
import { formatPct } from '@/lib/utils/format';
import { useMarketSummary } from '@/lib/api/queries/dashboard';

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: '메인',
    items: [
      { href: ROUTES.DASHBOARD, label: '대시보드', icon: LayoutDashboard },
      { href: ROUTES.RECOMMENDATIONS, label: '추천주', icon: Star },
      { href: ROUTES.CHART('005930'), label: '차트분석', icon: LineChart },
      { href: ROUTES.SECTORS, label: '업종분석', icon: PieChart },
      { href: ROUTES.SIGNALS, label: '매매 시그널', icon: Activity },
    ],
  },
  {
    title: '매매',
    items: [
      { href: ROUTES.AUTO_TRADING, label: '자동매매', icon: Cog },
      { href: ROUTES.REPORT, label: '수익률 리포트', icon: Sigma },
      { href: ROUTES.BACKTEST, label: '백테스트', icon: Timer },
    ],
  },
  {
    title: '설정',
    items: [
      { href: ROUTES.SETTINGS, label: '설정', icon: BarChart3 },
      { href: ROUTES.LOGIN, label: '로그아웃', icon: LogOut },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const market = useMarketSummary();

  return (
    <aside className="app-shell__sidebar app-sidebar" aria-label="주요 메뉴">
      <Link href={ROUTES.DASHBOARD} className="app-sidebar__brand">
        <span className="app-sidebar__brand-mark">T</span>
        <span className="app-sidebar__brand-name">TradePilot</span>
      </Link>

      <nav className="stack gap-1">
        {SECTIONS.map((section) => (
          <div key={section.title} className="stack">
            <p className="app-sidebar__section-label">{section.title}</p>
            {section.items.map((item) => {
              const Icon = item.icon;
              // 차트는 동적 코드라 prefix로만 비교
              const active = item.href === ROUTES.CHART('005930')
                ? pathname?.startsWith('/chart')
                : pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn('app-sidebar__item', active && 'app-sidebar__item--active')}
                >
                  <Icon className="h-[18px] w-[18px] flex-none" aria-hidden="true" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <Card ghost className="mt-8 p-3">
        <p className="text-xs text-subtle mb-2">시장 상태</p>
        <p className="text-sm">
          <Badge variant="success" dot>
            {market.data?.market_status === 'OPEN' ? '정규장' : '장 외'}
          </Badge>
        </p>
        {market.data && (
          <>
            <p className="text-xs text-muted mt-2">
              KOSPI {market.data.kospi.value.toLocaleString('ko-KR', { minimumFractionDigits: 2 })}{' '}
              <span className={market.data.kospi.change >= 0 ? 'text-up' : 'text-down'}>
                {market.data.kospi.change >= 0 ? '▲' : '▼'} {formatPct(market.data.kospi.change_pct)}
              </span>
            </p>
            <p className="text-xs text-muted">
              KOSDAQ {market.data.kosdaq.value.toLocaleString('ko-KR', { minimumFractionDigits: 2 })}{' '}
              <span className={market.data.kosdaq.change >= 0 ? 'text-up' : 'text-down'}>
                {market.data.kosdaq.change >= 0 ? '▲' : '▼'} {formatPct(market.data.kosdaq.change_pct)}
              </span>
            </p>
          </>
        )}
      </Card>
    </aside>
  );
}
