"""시그널 이력 익스포트 추출기."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Signal
from app.models.market import Stock


async def extract_signals(
    db: AsyncSession,
    user_id: int,
    filter_params: Mapping[str, Any],
) -> dict[str, pd.DataFrame]:
    """시그널 이력을 단일 시트로 반환."""
    today = date.today()
    from_str = filter_params.get("from") or filter_params.get("from_date")
    to_str = filter_params.get("to") or filter_params.get("to_date")
    from_d = date.fromisoformat(from_str) if from_str else today.replace(day=1)
    to_d = date.fromisoformat(to_str) if to_str else today
    from_dt = datetime.combine(from_d, datetime.min.time(), tzinfo=timezone.utc)
    to_dt = datetime.combine(to_d, datetime.max.time(), tzinfo=timezone.utc)

    stmt = (
        select(
            Signal.public_id,
            Signal.action,
            Signal.confidence,
            Signal.trigger_price,
            Signal.status,
            Signal.generated_at,
            Signal.expires_at,
            Stock.code,
            Stock.name,
        )
        .join(Stock, Stock.id == Signal.stock_id)
        .where(
            and_(
                Signal.user_id == user_id,
                Signal.generated_at >= from_dt,
                Signal.generated_at <= to_dt,
            )
        )
        .order_by(Signal.generated_at.desc())
    )
    if filter_params.get("code"):
        stmt = stmt.where(Stock.code == str(filter_params["code"]))
    if filter_params.get("action"):
        stmt = stmt.where(Signal.action == str(filter_params["action"]).upper())

    rows = (await db.execute(stmt)).all()
    df = pd.DataFrame(
        [
            {
                "signal_id": str(r.public_id),
                "code": r.code,
                "name": r.name,
                "side": r.action,
                "score": r.confidence,
                "price": _to_num(r.trigger_price),
                "status": r.status,
                "triggered_at": r.generated_at,
                "expires_at": r.expires_at,
            }
            for r in rows
        ],
        columns=[
            "signal_id", "code", "name", "side", "score",
            "price", "status", "triggered_at", "expires_at",
        ],
    )
    return {"시그널이력": df}


def _to_num(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return v
