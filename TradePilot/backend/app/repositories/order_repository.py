"""주문 도메인 Repository."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Stock
from app.models.trade import Fill, Order, Position, TradeLimit
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    model = Order

    async def find_by_public_id(self, public_id: UUID | str) -> Order | None:
        if isinstance(public_id, str):
            try:
                public_id = UUID(public_id)
            except ValueError:
                return None
        stmt = select(Order).where(Order.public_id == public_id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def find_by_idempotency_key(
        self, user_id: int, key: str, within_hours: int = 24
    ) -> Order | None:
        """멱등성 키 기반 기존 주문 탐색."""
        if not key:
            return None
        stmt = (
            select(Order)
            .where(
                and_(
                    Order.user_id == user_id,
                    Order.idempotency_key == key,
                )
            )
            .order_by(Order.ordered_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def count_daily_buys(self, user_id: int, today: date) -> int:
        """오늘 매수 주문 건수."""
        start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        end = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
        stmt = (
            select(func.count(Order.id))
            .where(
                and_(
                    Order.user_id == user_id,
                    Order.side == "BUY",
                    Order.status != "REJECTED",
                    Order.ordered_at >= start,
                    Order.ordered_at <= end,
                )
            )
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def sum_daily_buy_amount(self, user_id: int, today: date) -> Decimal:
        """오늘 매수 금액 합계 (체결가 기준, FILLED만 집계 - 단순화)."""
        start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        end = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
        stmt = (
            select(func.coalesce(func.sum(Fill.fill_qty * Fill.fill_price), 0))
            .where(
                and_(
                    Fill.user_id == user_id,
                    Fill.filled_at >= start,
                    Fill.filled_at <= end,
                )
            )
        )
        val = (await self.session.execute(stmt)).scalar_one()
        return Decimal(str(val or 0))

    async def list_for_user(
        self,
        user_id: int,
        *,
        status: str | None = None,
        code: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Order], int]:
        stmt = select(Order).where(Order.user_id == user_id)
        cnt_stmt = select(func.count(Order.id)).where(Order.user_id == user_id)

        if status:
            stmt = stmt.where(Order.status == status)
            cnt_stmt = cnt_stmt.where(Order.status == status)
        if code:
            stmt = stmt.join(Stock, Stock.id == Order.stock_id).where(Stock.code == code)
            cnt_stmt = cnt_stmt.join(Stock, Stock.id == Order.stock_id).where(Stock.code == code)
        if from_dt:
            stmt = stmt.where(Order.ordered_at >= from_dt)
            cnt_stmt = cnt_stmt.where(Order.ordered_at >= from_dt)
        if to_dt:
            stmt = stmt.where(Order.ordered_at <= to_dt)
            cnt_stmt = cnt_stmt.where(Order.ordered_at <= to_dt)

        stmt = stmt.order_by(Order.ordered_at.desc()).offset(offset).limit(limit)

        rows = (await self.session.execute(stmt)).scalars().all()
        total = int((await self.session.execute(cnt_stmt)).scalar_one() or 0)
        return list(rows), total


class StockRepository(BaseRepository[Stock]):
    model = Stock

    async def find_by_code(self, code: str) -> Stock | None:
        stmt = select(Stock).where(Stock.code == code).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()


class FillRepository(BaseRepository[Fill]):
    model = Fill


class PositionRepository(BaseRepository[Position]):
    model = Position

    async def find(self, user_id: int, stock_id: int, trade_mode: str) -> Position | None:
        stmt = select(Position).where(
            and_(
                Position.user_id == user_id,
                Position.stock_id == stock_id,
                Position.trade_mode == trade_mode,
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def count_active(self, user_id: int, trade_mode: str) -> int:
        stmt = select(func.count(Position.id)).where(
            and_(
                Position.user_id == user_id,
                Position.trade_mode == trade_mode,
                Position.qty > 0,
            )
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)


class TradeLimitRepository(BaseRepository[TradeLimit]):
    model = TradeLimit

    async def find_or_default(self, user_id: int) -> TradeLimit:
        existing = await self.get(user_id)
        if existing:
            return existing
        limit = TradeLimit(user_id=user_id)
        self.session.add(limit)
        await self.session.flush()
        return limit
