"""포트폴리오 서비스."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.factory import get_market_data
from app.repositories.portfolio_repository import (
    DailyPnlRepository,
    PortfolioRepository,
)

log = structlog.get_logger(__name__)


class PortfolioService:
    """포트폴리오 조회 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PortfolioRepository(db)
        self.pnl_repo = DailyPnlRepository(db)

    async def summary(self, user_id: int, trade_mode: str) -> dict[str, Any]:
        latest = await self.repo.latest_snapshot(user_id, trade_mode)
        cash = latest.cash if latest else Decimal("0")
        equity = latest.equity if latest else Decimal("0")
        total_value = latest.total_value if latest else Decimal("0")

        # 일일 PnL
        today_pnl = await self.pnl_repo.list_for_period(
            user_id, trade_mode, from_date=date.today(), to_date=date.today()
        )
        d_pnl = today_pnl[0].total_pnl if today_pnl else Decimal("0")
        d_pnl_pct = (
            Decimal(round(float(d_pnl) / float(total_value) * 100, 4))
            if total_value
            else Decimal("0")
        )

        # 활성 포지션 카운트
        rows, _total = await self.repo.positions_with_stock(
            user_id, trade_mode, offset=0, limit=1
        )
        _, position_total = await self.repo.positions_with_stock(
            user_id, trade_mode, offset=0, limit=1
        )

        return {
            "total_value": total_value,
            "cash": cash,
            "equity": equity,
            "daily_pnl": d_pnl,
            "daily_pnl_pct": d_pnl_pct,
            "position_count": position_total,
        }

    async def positions(
        self, user_id: int, trade_mode: str, *, offset: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        rows, total = await self.repo.positions_with_stock(
            user_id, trade_mode, offset=offset, limit=limit
        )
        market = get_market_data(trade_mode)
        items: list[dict[str, Any]] = []
        for pos, stock in rows:
            current_price: Decimal | None = None
            try:
                snap = await market.get_snapshot(stock.code)
                current_price = snap.price
            except Exception:
                current_price = None
            unrealized = None
            unrealized_pct = None
            if current_price is not None and pos.qty > 0:
                unrealized = (current_price - pos.avg_price) * pos.qty
                unrealized_pct = (
                    (current_price - pos.avg_price) / pos.avg_price * 100
                    if pos.avg_price
                    else None
                )
            items.append(
                {
                    "code": stock.code,
                    "name": stock.name,
                    "qty": pos.qty,
                    "avg_price": pos.avg_price,
                    "current_price": current_price,
                    "unrealized_pnl": unrealized,
                    "unrealized_pnl_pct": unrealized_pct,
                    "realized_pnl": pos.realized_pnl,
                    "trade_mode": pos.trade_mode,
                }
            )
        return items, total

    async def history(
        self,
        user_id: int,
        trade_mode: str,
        *,
        from_date: date,
        to_date: date,
        granularity: str = "D",
    ) -> list[dict[str, Any]]:
        rows = await self.repo.history(
            user_id,
            trade_mode,
            from_dt=datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc),
            to_dt=datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc),
        )
        items = [
            {
                "ts": r.snapshot_at.date(),
                "cash": r.cash,
                "equity": r.equity,
                "total_value": r.total_value,
            }
            for r in rows
        ]
        if granularity in ("W", "M") and items:
            # 주/월 단위 마지막 스냅샷만 추출
            from collections import OrderedDict

            groups: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
            for it in items:
                ts: date = it["ts"]
                key = ts.strftime("%Y-%W") if granularity == "W" else ts.strftime("%Y-%m")
                groups[key] = it
            items = list(groups.values())
        return items

    async def realized_pnl(
        self,
        user_id: int,
        trade_mode: str,
        *,
        from_date: date,
        to_date: date,
    ) -> dict[str, Any]:
        rows = await self.pnl_repo.list_for_period(
            user_id, trade_mode, from_date=from_date, to_date=to_date
        )
        items = [
            {
                "trade_date": r.trade_date,
                "realized_pnl": r.realized_pnl,
                "win_count": r.win_count,
                "loss_count": r.loss_count,
            }
            for r in rows
        ]
        total = sum((r.realized_pnl or 0) for r in rows)
        wins = sum((r.win_count or 0) for r in rows)
        losses = sum((r.loss_count or 0) for r in rows)
        win_rate = round(wins / (wins + losses), 4) if (wins + losses) else 0.0
        return {
            "total_pnl": Decimal(str(total)),
            "win_count": int(wins),
            "loss_count": int(losses),
            "win_rate": win_rate,
            "items": items,
        }
