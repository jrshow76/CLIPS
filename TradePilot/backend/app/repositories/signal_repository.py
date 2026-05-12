"""시그널 Repository."""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select

from app.models.analysis import Signal
from app.models.market import Stock
from app.repositories.base import BaseRepository


class SignalRepository(BaseRepository[Signal]):
    model = Signal

    async def find_by_public_id(self, public_id: str | UUID) -> Signal | None:
        if isinstance(public_id, str):
            try:
                public_id = UUID(public_id)
            except ValueError:
                return None
        stmt = select(Signal).where(Signal.public_id == public_id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: int,
        *,
        status: str | None = None,
        strategy_id: int | None = None,
        code: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[Signal, Stock]], int]:
        stmt = (
            select(Signal, Stock)
            .join(Stock, Stock.id == Signal.stock_id)
            .where(Signal.user_id == user_id)
        )
        cnt = select(func.count(Signal.id)).where(Signal.user_id == user_id)

        if status:
            stmt = stmt.where(Signal.status == status)
            cnt = cnt.where(Signal.status == status)
        if strategy_id is not None:
            stmt = stmt.where(Signal.strategy_id == strategy_id)
            cnt = cnt.where(Signal.strategy_id == strategy_id)
        if code:
            stmt = stmt.where(Stock.code == code)
            cnt = cnt.join(Stock, Stock.id == Signal.stock_id).where(Stock.code == code)
        if from_dt:
            stmt = stmt.where(Signal.generated_at >= from_dt)
            cnt = cnt.where(Signal.generated_at >= from_dt)
        if to_dt:
            stmt = stmt.where(Signal.generated_at <= to_dt)
            cnt = cnt.where(Signal.generated_at <= to_dt)

        stmt = stmt.order_by(Signal.generated_at.desc()).offset(offset).limit(limit)
        rows = (await self.session.execute(stmt)).all()
        total = int((await self.session.execute(cnt)).scalar_one() or 0)
        return [(r[0], r[1]) for r in rows], total

    async def count_summary(self, user_id: int) -> dict[str, int]:
        """오늘 시그널 / 활성 / 무시 카운트."""
        today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
        active_q = (
            await self.session.execute(
                select(func.count(Signal.id)).where(
                    and_(Signal.user_id == user_id, Signal.status == "ACTIVE")
                )
            )
        ).scalar_one() or 0
        today_q = (
            await self.session.execute(
                select(func.count(Signal.id)).where(
                    and_(Signal.user_id == user_id, Signal.generated_at >= today_start)
                )
            )
        ).scalar_one() or 0
        ignored_q = (
            await self.session.execute(
                select(func.count(Signal.id)).where(
                    and_(Signal.user_id == user_id, Signal.status == "IGNORED")
                )
            )
        ).scalar_one() or 0
        return {"active": int(active_q), "today": int(today_q), "ignored": int(ignored_q)}
