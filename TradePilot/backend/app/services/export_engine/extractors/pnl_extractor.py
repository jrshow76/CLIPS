"""일별 PnL 익스포트 추출기.

시트:
    * 일별 - daily_pnl 행 그대로
    * 월별 - 월 단위 합계 (realized + unrealized + total)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Mapping

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import DailyPnl


async def extract_pnl(
    db: AsyncSession,
    user_id: int,
    filter_params: Mapping[str, Any],
) -> dict[str, pd.DataFrame]:
    """일별/월별 PnL DataFrame 반환."""
    today = date.today()
    from_str = filter_params.get("from") or filter_params.get("from_date")
    to_str = filter_params.get("to") or filter_params.get("to_date")
    from_d = date.fromisoformat(from_str) if from_str else today.replace(month=1, day=1)
    to_d = date.fromisoformat(to_str) if to_str else today

    stmt = (
        select(DailyPnl)
        .where(
            and_(
                DailyPnl.user_id == user_id,
                DailyPnl.trade_date >= from_d,
                DailyPnl.trade_date <= to_d,
            )
        )
        .order_by(DailyPnl.trade_date.asc())
    )
    rows = list((await db.execute(stmt)).scalars().all())

    daily_df = pd.DataFrame(
        [
            {
                "trade_date": r.trade_date,
                "trade_mode": r.trade_mode,
                "realized_pnl": _to_num(r.realized_pnl),
                "unrealized_pnl": _to_num(r.unrealized_pnl),
                "total_pnl": _to_num(r.total_pnl),
                "mdd": _to_num(r.mdd),
                "win_count": r.win_count or 0,
                "loss_count": r.loss_count or 0,
            }
            for r in rows
        ],
        columns=[
            "trade_date", "trade_mode", "realized_pnl", "unrealized_pnl",
            "total_pnl", "mdd", "win_count", "loss_count",
        ],
    )

    # 월별 집계
    if not daily_df.empty:
        tmp = daily_df.copy()
        tmp["월"] = pd.to_datetime(tmp["trade_date"]).dt.strftime("%Y-%m")
        agg = (
            tmp.groupby("월", as_index=False)
            .agg(
                realized_pnl=("realized_pnl", "sum"),
                unrealized_pnl=("unrealized_pnl", "sum"),
                total_pnl=("total_pnl", "sum"),
                win_count=("win_count", "sum"),
                loss_count=("loss_count", "sum"),
            )
        )
        # 승률 계산 (분모 0 보호)
        total = agg["win_count"] + agg["loss_count"]
        agg["win_rate"] = (agg["win_count"] / total.where(total > 0, 1)).where(total > 0, 0.0)
        monthly_df = agg
    else:
        monthly_df = pd.DataFrame(
            columns=[
                "월", "realized_pnl", "unrealized_pnl", "total_pnl",
                "win_count", "loss_count", "win_rate",
            ]
        )

    return {"일별": daily_df, "월별": monthly_df}


def _to_num(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return v
