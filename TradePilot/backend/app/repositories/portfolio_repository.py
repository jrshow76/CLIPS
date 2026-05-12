"""포트폴리오 Repository."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import and_, desc, func, select

from app.models.market import Stock
from app.models.trade import DailyPnl, Portfolio, Position
from app.repositories.base import BaseRepository


class PortfolioRepository(BaseRepository[Portfolio]):
    model = Portfolio

    async def latest_snapshot(self, user_id: int, trade_mode: str) -> Portfolio | None:
        stmt = (
            select(Portfolio)
            .where(and_(Portfolio.user_id == user_id, Portfolio.trade_mode == trade_mode))
            .order_by(desc(Portfolio.snapshot_at))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def history(
        self,
        user_id: int,
        trade_mode: str,
        *,
        from_dt: datetime | None,
        to_dt: datetime | None,
    ) -> list[Portfolio]:
        stmt = select(Portfolio).where(
            and_(Portfolio.user_id == user_id, Portfolio.trade_mode == trade_mode)
        )
        if from_dt:
            stmt = stmt.where(Portfolio.snapshot_at >= from_dt)
        if to_dt:
            stmt = stmt.where(Portfolio.snapshot_at <= to_dt)
        stmt = stmt.order_by(Portfolio.snapshot_at.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def positions_with_stock(
        self, user_id: int, trade_mode: str, *, offset: int, limit: int
    ) -> tuple[list[tuple[Position, Stock]], int]:
        stmt = (
            select(Position, Stock)
            .join(Stock, Stock.id == Position.stock_id)
            .where(
                and_(
                    Position.user_id == user_id,
                    Position.trade_mode == trade_mode,
                    Position.qty > 0,
                )
            )
            .order_by(Position.opened_at.desc())
            .offset(offset)
            .limit(limit)
        )
        cnt = select(func.count(Position.id)).where(
            and_(
                Position.user_id == user_id,
                Position.trade_mode == trade_mode,
                Position.qty > 0,
            )
        )
        rows = (await self.session.execute(stmt)).all()
        total = int((await self.session.execute(cnt)).scalar_one() or 0)
        return [(r[0], r[1]) for r in rows], total


class DailyPnlRepository(BaseRepository[DailyPnl]):
    model = DailyPnl

    async def list_for_period(
        self,
        user_id: int,
        trade_mode: str,
        *,
        from_date: date,
        to_date: date,
    ) -> list[DailyPnl]:
        stmt = (
            select(DailyPnl)
            .where(
                and_(
                    DailyPnl.user_id == user_id,
                    DailyPnl.trade_mode == trade_mode,
                    DailyPnl.trade_date >= from_date,
                    DailyPnl.trade_date <= to_date,
                )
            )
            .order_by(DailyPnl.trade_date.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())
