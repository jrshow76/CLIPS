"""거래내역 익스포트 추출기.

필터:
    * ``from`` / ``to`` (ISO date) - 기간(필수)
    * ``code`` - 종목코드(선택)
    * ``status`` - 주문 상태(선택)

시트:
    * 주문(orders) - 주문 단위 요약
    * 체결(fills) - 체결 단위 상세
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Stock
from app.models.trade import Fill, Order


def _parse_period(filter_params: Mapping[str, Any]) -> tuple[datetime, datetime]:
    """from/to 파싱. 누락 시 최근 1개월."""
    today = date.today()
    from_str = filter_params.get("from") or filter_params.get("from_date")
    to_str = filter_params.get("to") or filter_params.get("to_date")
    from_d = date.fromisoformat(from_str) if from_str else today.replace(day=1)
    to_d = date.fromisoformat(to_str) if to_str else today
    from_dt = datetime.combine(from_d, datetime.min.time(), tzinfo=timezone.utc)
    to_dt = datetime.combine(to_d, datetime.max.time(), tzinfo=timezone.utc)
    return from_dt, to_dt


async def extract_orders(
    db: AsyncSession,
    user_id: int,
    filter_params: Mapping[str, Any],
) -> dict[str, pd.DataFrame]:
    """사용자 주문/체결을 두 시트의 DataFrame 으로 반환.

    Returns:
        ``{"주문": orders_df, "체결": fills_df}``
    """
    from_dt, to_dt = _parse_period(filter_params)
    code_filter = filter_params.get("code")
    status_filter = filter_params.get("status")

    # 주문 + 종목 조인
    stmt = (
        select(
            Order.public_id,
            Order.side,
            Order.order_type,
            Order.trade_mode,
            Order.qty,
            Order.price,
            Order.status,
            Order.ordered_at,
            Order.filled_at,
            Order.canceled_at,
            Order.broker_order_no,
            Order.reject_reason,
            Stock.code,
            Stock.name,
        )
        .join(Stock, Stock.id == Order.stock_id)
        .where(
            and_(
                Order.user_id == user_id,
                Order.ordered_at >= from_dt,
                Order.ordered_at <= to_dt,
            )
        )
        .order_by(Order.ordered_at.desc())
    )
    if code_filter:
        stmt = stmt.where(Stock.code == str(code_filter))
    if status_filter:
        stmt = stmt.where(Order.status == str(status_filter).upper())

    rows = (await db.execute(stmt)).all()
    orders_df = pd.DataFrame(
        [
            {
                "public_id": str(r.public_id),
                "code": r.code,
                "name": r.name,
                "side": r.side,
                "order_type": r.order_type,
                "trade_mode": r.trade_mode,
                "qty": _to_num(r.qty),
                "price": _to_num(r.price),
                "status": r.status,
                "ordered_at": r.ordered_at,
                "filled_at": r.filled_at,
                "canceled_at": r.canceled_at,
                "broker_order_no": r.broker_order_no,
                "reject_reason": r.reject_reason,
            }
            for r in rows
        ],
        columns=[
            "public_id", "code", "name", "side", "order_type", "trade_mode",
            "qty", "price", "status",
            "ordered_at", "filled_at", "canceled_at",
            "broker_order_no", "reject_reason",
        ],
    )

    # 체결 시트
    fstmt = (
        select(
            Fill.id,
            Fill.fill_qty,
            Fill.fill_price,
            Fill.fee,
            Fill.tax,
            Fill.slippage,
            Fill.filled_at,
            Stock.code,
            Stock.name,
        )
        .join(Stock, Stock.id == Fill.stock_id)
        .where(
            and_(
                Fill.user_id == user_id,
                Fill.filled_at >= from_dt,
                Fill.filled_at <= to_dt,
            )
        )
        .order_by(Fill.filled_at.desc())
    )
    if code_filter:
        fstmt = fstmt.where(Stock.code == str(code_filter))

    fillrows = (await db.execute(fstmt)).all()
    fills_df = pd.DataFrame(
        [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "fill_qty": _to_num(r.fill_qty),
                "fill_price": _to_num(r.fill_price),
                "fee": _to_num(r.fee),
                "tax": _to_num(r.tax),
                "slippage": _to_num(r.slippage),
                "filled_at": r.filled_at,
                "amount": _to_num(r.fill_qty) * _to_num(r.fill_price) if r.fill_qty and r.fill_price else 0,
            }
            for r in fillrows
        ],
        columns=[
            "id", "code", "name", "fill_qty", "fill_price",
            "fee", "tax", "slippage", "filled_at", "amount",
        ],
    )

    return {"주문": orders_df, "체결": fills_df}


def _to_num(v):
    """Decimal/None 안전 변환."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return v
