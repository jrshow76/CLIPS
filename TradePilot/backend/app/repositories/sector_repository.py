"""섹터 도메인 Repository."""
from __future__ import annotations

from datetime import date

from sqlalchemy import and_, desc, func, select

from app.models.analysis import SectorMetricsDaily
from app.models.market import Sector, Stock, StockSector
from app.repositories.base import BaseRepository


class SectorRepository(BaseRepository[Sector]):
    model = Sector

    async def list_all(self) -> list[Sector]:
        stmt = select(Sector).order_by(Sector.sort_order.asc(), Sector.name.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def find_by_code(self, code: str) -> Sector | None:
        stmt = select(Sector).where(Sector.code == code).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_stocks(
        self, sector_id: int, *, offset: int, limit: int
    ) -> tuple[list[tuple[Stock, bool]], int]:
        stmt = (
            select(Stock, StockSector.is_primary)
            .join(StockSector, StockSector.stock_id == Stock.id)
            .where(StockSector.sector_id == sector_id)
            .order_by(Stock.code.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        cnt = (
            await self.session.execute(
                select(func.count(StockSector.stock_id)).where(
                    StockSector.sector_id == sector_id
                )
            )
        ).scalar_one()
        return [(r[0], bool(r[1])) for r in rows], int(cnt or 0)

    async def metrics_for_period(
        self, sector_id: int, *, from_date: date, to_date: date
    ) -> list[SectorMetricsDaily]:
        stmt = (
            select(SectorMetricsDaily)
            .where(
                and_(
                    SectorMetricsDaily.sector_id == sector_id,
                    SectorMetricsDaily.trade_date >= from_date,
                    SectorMetricsDaily.trade_date <= to_date,
                )
            )
            .order_by(SectorMetricsDaily.trade_date.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def latest_metrics_all(self) -> list[tuple[Sector, SectorMetricsDaily | None]]:
        """모든 섹터의 최신 메트릭."""
        sectors = await self.list_all()
        result: list[tuple[Sector, SectorMetricsDaily | None]] = []
        for s in sectors:
            stmt = (
                select(SectorMetricsDaily)
                .where(SectorMetricsDaily.sector_id == s.id)
                .order_by(desc(SectorMetricsDaily.trade_date))
                .limit(1)
            )
            m = (await self.session.execute(stmt)).scalar_one_or_none()
            result.append((s, m))
        return result
