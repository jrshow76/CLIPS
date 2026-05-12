"""추천주 Repository."""
from __future__ import annotations

from datetime import date

from sqlalchemy import and_, desc, func, select

from app.models.analysis import Recommendation
from app.models.market import Stock, StockSector
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    model = Recommendation

    async def list_by_filters(
        self,
        *,
        strategy_id: int | None = None,
        sector_id: int | None = None,
        market_cap_min: int | None = None,
        market_cap_max: int | None = None,
        trade_date: date | None = None,
        sort: str = "score,desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[Recommendation, Stock]], int]:
        if trade_date is None:
            latest_q = await self.session.execute(select(func.max(Recommendation.trade_date)))
            trade_date = latest_q.scalar_one_or_none() or date.today()

        stmt = (
            select(Recommendation, Stock)
            .join(Stock, Stock.id == Recommendation.stock_id)
            .where(Recommendation.trade_date == trade_date)
        )
        cnt = (
            select(func.count(Recommendation.id))
            .join(Stock, Stock.id == Recommendation.stock_id)
            .where(Recommendation.trade_date == trade_date)
        )
        if strategy_id is not None:
            stmt = stmt.where(Recommendation.strategy_id == strategy_id)
            cnt = cnt.where(Recommendation.strategy_id == strategy_id)
        if sector_id is not None:
            stmt = stmt.join(StockSector, StockSector.stock_id == Stock.id).where(
                StockSector.sector_id == sector_id
            )
            cnt = cnt.join(StockSector, StockSector.stock_id == Stock.id).where(
                StockSector.sector_id == sector_id
            )
        if market_cap_min is not None:
            stmt = stmt.where(Stock.market_cap >= market_cap_min)
            cnt = cnt.where(Stock.market_cap >= market_cap_min)
        if market_cap_max is not None:
            stmt = stmt.where(Stock.market_cap <= market_cap_max)
            cnt = cnt.where(Stock.market_cap <= market_cap_max)

        # 정렬
        field, _, direction = sort.partition(",")
        direction = direction or "desc"
        col_map = {
            "score": Recommendation.score,
            "change_pct": Recommendation.score,  # change_pct는 features에 있음 - 단순화: score 기준
            "volume": Stock.market_cap,
        }
        col = col_map.get(field, Recommendation.score)
        stmt = stmt.order_by(col.desc() if direction == "desc" else col.asc())
        stmt = stmt.offset(offset).limit(limit)

        rows = (await self.session.execute(stmt)).all()
        total = int((await self.session.execute(cnt)).scalar_one() or 0)
        return [(r[0], r[1]) for r in rows], total

    async def top_n(self, limit: int = 5, trade_date: date | None = None) -> list[tuple[Recommendation, Stock]]:
        if trade_date is None:
            r = await self.session.execute(select(func.max(Recommendation.trade_date)))
            trade_date = r.scalar_one_or_none() or date.today()
        stmt = (
            select(Recommendation, Stock)
            .join(Stock, Stock.id == Recommendation.stock_id)
            .where(Recommendation.trade_date == trade_date)
            .order_by(desc(Recommendation.score))
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(r[0], r[1]) for r in rows]

    async def find_by_code(
        self, code: str, trade_date: date | None = None
    ) -> tuple[Recommendation, Stock] | None:
        if trade_date is None:
            r = await self.session.execute(select(func.max(Recommendation.trade_date)))
            trade_date = r.scalar_one_or_none() or date.today()
        stmt = (
            select(Recommendation, Stock)
            .join(Stock, Stock.id == Recommendation.stock_id)
            .where(and_(Stock.code == code, Recommendation.trade_date == trade_date))
            .order_by(desc(Recommendation.score))
            .limit(1)
        )
        row = (await self.session.execute(stmt)).first()
        return (row[0], row[1]) if row else None
