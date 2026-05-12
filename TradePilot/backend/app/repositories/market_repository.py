"""시장 지수 Repository."""
from __future__ import annotations

from datetime import date

from sqlalchemy import desc, select

from app.models.market import MarketIndex, MarketIndexDaily
from app.repositories.base import BaseRepository


class MarketIndexRepository(BaseRepository[MarketIndex]):
    model = MarketIndex

    async def list_all(self) -> list[MarketIndex]:
        stmt = select(MarketIndex).order_by(MarketIndex.code.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def find_by_code(self, code: str) -> MarketIndex | None:
        stmt = select(MarketIndex).where(MarketIndex.code == code).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest_daily(self, index_id: int) -> MarketIndexDaily | None:
        stmt = (
            select(MarketIndexDaily)
            .where(MarketIndexDaily.index_id == index_id)
            .order_by(desc(MarketIndexDaily.trade_date))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_daily(
        self,
        index_id: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MarketIndexDaily]:
        stmt = select(MarketIndexDaily).where(MarketIndexDaily.index_id == index_id)
        if from_date:
            stmt = stmt.where(MarketIndexDaily.trade_date >= from_date)
        if to_date:
            stmt = stmt.where(MarketIndexDaily.trade_date <= to_date)
        stmt = stmt.order_by(MarketIndexDaily.trade_date.asc())
        return list((await self.session.execute(stmt)).scalars().all())
