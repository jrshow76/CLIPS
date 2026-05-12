"""백테스트 Repository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select

from app.models.backtest import BacktestResult, BacktestRun, BacktestTrade
from app.repositories.base import BaseRepository


class BacktestRunRepository(BaseRepository[BacktestRun]):
    model = BacktestRun

    async def find_by_job_id(self, job_id: str | UUID) -> BacktestRun | None:
        if isinstance(job_id, str):
            try:
                job_id = UUID(job_id)
            except ValueError:
                return None
        stmt = select(BacktestRun).where(BacktestRun.job_id == job_id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()


class BacktestResultRepository(BaseRepository[BacktestResult]):
    model = BacktestResult

    async def list_saved_for_user(
        self, user_id: int, *, offset: int, limit: int
    ) -> tuple[list[tuple[BacktestResult, BacktestRun]], int]:
        stmt = (
            select(BacktestResult, BacktestRun)
            .join(BacktestRun, BacktestRun.id == BacktestResult.run_id)
            .where(BacktestRun.user_id == user_id)
            .order_by(desc(BacktestResult.saved_at))
            .offset(offset)
            .limit(limit)
        )
        cnt = (
            select(func.count(BacktestResult.run_id))
            .join(BacktestRun, BacktestRun.id == BacktestResult.run_id)
            .where(BacktestRun.user_id == user_id)
        )
        rows = (await self.session.execute(stmt)).all()
        total = int((await self.session.execute(cnt)).scalar_one() or 0)
        return [(r[0], r[1]) for r in rows], total


class BacktestTradeRepository(BaseRepository[BacktestTrade]):
    model = BacktestTrade

    async def list_for_run(self, run_id: int) -> list[BacktestTrade]:
        stmt = (
            select(BacktestTrade)
            .where(BacktestTrade.run_id == run_id)
            .order_by(BacktestTrade.entry_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())
