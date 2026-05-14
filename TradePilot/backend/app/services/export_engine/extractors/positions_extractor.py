"""보유 종목 익스포트 추출기."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Stock
from app.models.trade import Position


async def extract_positions(
    db: AsyncSession,
    user_id: int,
    filter_params: Mapping[str, Any],
) -> dict[str, pd.DataFrame]:
    """현재 보유 포지션을 단일 시트로 반환."""
    trade_mode = filter_params.get("trade_mode")

    stmt = (
        select(
            Stock.code,
            Stock.name,
            Position.trade_mode,
            Position.qty,
            Position.avg_price,
            Position.realized_pnl,
            Position.opened_at,
            Position.updated_at,
        )
        .join(Stock, Stock.id == Position.stock_id)
        .where(Position.user_id == user_id)
        .order_by(Position.opened_at.desc())
    )
    if trade_mode:
        stmt = stmt.where(Position.trade_mode == str(trade_mode).upper())

    rows = (await db.execute(stmt)).all()
    df = pd.DataFrame(
        [
            {
                "code": r.code,
                "name": r.name,
                "trade_mode": r.trade_mode,
                "qty": _to_num(r.qty),
                "avg_price": _to_num(r.avg_price),
                "realized_pnl": _to_num(r.realized_pnl),
                "amount": _to_num(r.qty) * _to_num(r.avg_price) if r.qty and r.avg_price else 0,
                "created_at": r.opened_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
        columns=[
            "code", "name", "trade_mode", "qty", "avg_price",
            "realized_pnl", "amount", "created_at", "updated_at",
        ],
    )
    return {"보유종목": df}


def _to_num(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return v
