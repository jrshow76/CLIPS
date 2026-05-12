"""전략 Repository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select

from app.models.trade import Strategy
from app.repositories.base import BaseRepository


class StrategyRepository(BaseRepository[Strategy]):
    model = Strategy

    async def find_by_public_id(self, public_id: str | UUID) -> Strategy | None:
        if isinstance(public_id, str):
            try:
                public_id = UUID(public_id)
            except ValueError:
                return None
        stmt = select(Strategy).where(
            and_(Strategy.public_id == public_id, Strategy.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: int,
        *,
        active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Strategy], int]:
        stmt = select(Strategy).where(
            and_(Strategy.user_id == user_id, Strategy.deleted_at.is_(None))
        )
        cnt = select(func.count(Strategy.id)).where(
            and_(Strategy.user_id == user_id, Strategy.deleted_at.is_(None))
        )
        if active is not None:
            stmt = stmt.where(Strategy.active.is_(active))
            cnt = cnt.where(Strategy.active.is_(active))
        stmt = stmt.order_by(Strategy.created_at.desc()).offset(offset).limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        total = int((await self.session.execute(cnt)).scalar_one() or 0)
        return list(rows), total
