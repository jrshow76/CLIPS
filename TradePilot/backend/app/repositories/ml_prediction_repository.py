"""ML 예측 Repository."""
from __future__ import annotations

from datetime import date

from sqlalchemy import desc, select

from app.models.analysis import MLPrediction
from app.repositories.base import BaseRepository


class MLPredictionRepository(BaseRepository[MLPrediction]):
    model = MLPrediction

    async def list_for_stock(
        self, stock_id: int, *, base_date: date | None = None, limit: int = 5
    ) -> list[MLPrediction]:
        stmt = select(MLPrediction).where(MLPrediction.stock_id == stock_id)
        if base_date is not None:
            stmt = stmt.where(MLPrediction.base_date == base_date)
        else:
            # 최신 base_date 기준
            latest = await self.session.execute(
                select(MLPrediction.base_date)
                .where(MLPrediction.stock_id == stock_id)
                .order_by(desc(MLPrediction.base_date))
                .limit(1)
            )
            base = latest.scalar_one_or_none()
            if base:
                stmt = stmt.where(MLPrediction.base_date == base)
        stmt = stmt.order_by(MLPrediction.horizon.asc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def latest_accuracy(self, stock_id: int) -> MLPrediction | None:
        stmt = (
            select(MLPrediction)
            .where(MLPrediction.stock_id == stock_id)
            .order_by(desc(MLPrediction.base_date))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
