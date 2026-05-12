"""종목/시세 Repository.

`StockRepository`는 이미 `order_repository.py`에 정의되어 있으므로 본 파일은
검색 / 즐겨찾기 / 일봉·분봉 조회 등 부가 메서드를 모은다.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import and_, desc, func, select

from app.models.market import (
    PriceDaily,
    PriceMinute,
    Sector,
    Stock,
    StockSector,
)
from app.models.user import UserFavorite
from app.repositories.base import BaseRepository


class StockExtRepository(BaseRepository[Stock]):
    """검색/시세 부가 조회용 Stock Repository."""

    model = Stock

    async def find_by_code(self, code: str) -> Stock | None:
        stmt = select(Stock).where(Stock.code == code).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def search(
        self,
        *,
        q: str | None,
        market: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Stock], int]:
        stmt = select(Stock).where(Stock.status == "LISTED")
        cnt = select(func.count(Stock.id)).where(Stock.status == "LISTED")
        if q:
            like = f"%{q}%"
            stmt = stmt.where((Stock.name.ilike(like)) | (Stock.code.like(f"{q}%")))
            cnt = cnt.where((Stock.name.ilike(like)) | (Stock.code.like(f"{q}%")))
        if market:
            stmt = stmt.where(Stock.market == market)
            cnt = cnt.where(Stock.market == market)
        stmt = stmt.order_by(Stock.market.asc(), Stock.code.asc()).offset(offset).limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        total = int((await self.session.execute(cnt)).scalar_one() or 0)
        return list(rows), total

    async def get_primary_sector(self, stock_id: int) -> Sector | None:
        """종목의 1차 섹터."""
        stmt = (
            select(Sector)
            .join(StockSector, StockSector.sector_id == Sector.id)
            .where(
                and_(
                    StockSector.stock_id == stock_id,
                    StockSector.is_primary.is_(True),
                )
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_daily(
        self, stock_id: int, *, from_date: date | None, to_date: date | None, limit: int = 500
    ) -> list[PriceDaily]:
        stmt = select(PriceDaily).where(PriceDaily.stock_id == stock_id)
        if from_date:
            stmt = stmt.where(PriceDaily.trade_date >= from_date)
        if to_date:
            stmt = stmt.where(PriceDaily.trade_date <= to_date)
        stmt = stmt.order_by(PriceDaily.trade_date.asc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_minute(
        self,
        stock_id: int,
        *,
        interval_min: int,
        from_ts: datetime | None,
        to_ts: datetime | None,
        limit: int = 1000,
    ) -> list[PriceMinute]:
        stmt = select(PriceMinute).where(
            and_(
                PriceMinute.stock_id == stock_id,
                PriceMinute.interval_min == interval_min,
            )
        )
        if from_ts:
            stmt = stmt.where(PriceMinute.ts >= from_ts)
        if to_ts:
            stmt = stmt.where(PriceMinute.ts <= to_ts)
        stmt = stmt.order_by(PriceMinute.ts.asc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def latest_daily(self, stock_id: int) -> PriceDaily | None:
        """최근 일봉 1행."""
        stmt = (
            select(PriceDaily)
            .where(PriceDaily.stock_id == stock_id)
            .order_by(desc(PriceDaily.trade_date))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class UserFavoriteRepository(BaseRepository[UserFavorite]):
    model = UserFavorite

    async def exists(self, user_id: int, stock_id: int) -> bool:
        stmt = select(func.count(UserFavorite.user_id)).where(
            and_(UserFavorite.user_id == user_id, UserFavorite.stock_id == stock_id)
        )
        return bool((await self.session.execute(stmt)).scalar_one())

    async def list_for_user(self, user_id: int) -> list[tuple[UserFavorite, Stock]]:
        stmt = (
            select(UserFavorite, Stock)
            .join(Stock, Stock.id == UserFavorite.stock_id)
            .where(UserFavorite.user_id == user_id)
            .order_by(UserFavorite.created_at.desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [(r[0], r[1]) for r in rows]

    async def remove(self, user_id: int, stock_id: int) -> None:
        from sqlalchemy import delete

        await self.session.execute(
            delete(UserFavorite).where(
                and_(UserFavorite.user_id == user_id, UserFavorite.stock_id == stock_id)
            )
        )
